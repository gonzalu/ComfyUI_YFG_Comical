# =============================================================================
# Author      : Manny Gonzalez (YFG)
# Title       : YFG CivitAI MetaSave - Graph Tracer
# Nickname    : YFG_CivitAI_MetaSave
# Description : BFS-based tracer that walks the ComfyUI prompt graph upstream
#               from a given node, building a distance-annotated trace tree
#               used to identify which nodes contributed to a particular output.
#               Results are cached by graph signature to avoid redundant work.
# =============================================================================

from collections import deque, defaultdict
from .defs.samplers import SAMPLERS
from .utils.log import print_warning


class Trace:
    _trace_cache = {}

    @staticmethod
    def _bfs_traverse(start_node_id, prompt, visit_node, edge_condition=None):
        Q = deque([(start_node_id, 0)])
        visited_nodes = set()
        visited_edges = set()

        while Q:
            current_node_id, distance = Q.popleft()
            if current_node_id in visited_nodes or current_node_id not in prompt:
                continue
            visited_nodes.add(current_node_id)

            node = prompt[current_node_id]
            visit_node(current_node_id, node, distance)

            for value in node.get("inputs", {}).values():
                values = value if isinstance(value, list) else [value]

                for next_id in values:
                    if next_id is None:
                        continue

                    # Handle dict-based links (ComfyUI internal link structures)
                    if isinstance(next_id, dict):
                        next_id = next_id.get("link") or next_id.get("id") or next_id.get("node_id")

                    if next_id is None or isinstance(next_id, dict):
                        continue

                    next_id = str(next_id) if isinstance(next_id, int) else next_id

                    edge = (current_node_id, next_id)
                    if edge in visited_edges or (edge_condition and not edge_condition(current_node_id, next_id)):
                        continue

                    visited_edges.add(edge)
                    Q.append((next_id, distance + 1))

    @classmethod
    def _compute_trace_signature(cls, start_node_id, prompt):
        structure = []
        def collect(nid, node, _):
            structure.append((nid, node.get("class_type", "")))
        cls._bfs_traverse(start_node_id, prompt, collect)
        structure.sort()
        return hash(tuple(structure))

    @classmethod
    def trace(cls, start_node_id, prompt):
        sig = cls._compute_trace_signature(start_node_id, prompt)
        if sig in cls._trace_cache:
            return cls._trace_cache[sig]

        trace_tree = {}
        def build(nid, node, dist):
            trace_tree[nid] = (dist, node.get("class_type", ""))
        cls._bfs_traverse(start_node_id, prompt, build)
        cls._trace_cache[sig] = trace_tree
        return trace_tree

    @classmethod
    def find_node_by_class_types(cls, trace_tree, class_type_set, node_id=None):
        if node_id:
            node = trace_tree.get(node_id)
            if node and node[1] in class_type_set:
                return node_id
        else:
            for nid, (_, class_type) in trace_tree.items():
                if class_type in class_type_set:
                    return nid
        return None

    @classmethod
    def find_node_with_fields(cls, prompt, required_fields):
        for node_id, node in prompt.items():
            if required_fields & set(node.get("inputs", {}).keys()):
                return node_id, node
        return None, None

    @classmethod
    def find_all_nodes_with_fields(cls, prompt, required_fields):
        return [
            (node_id, node)
            for node_id, node in prompt.items()
            if required_fields & set(node.get("inputs", {}).keys())
        ]

    @classmethod
    def find_sampler_node_id(cls, trace_tree):
        node = cls.find_node_by_class_types(trace_tree, set(SAMPLERS.keys()))
        if node:
            return node
        print_warning("Could not find a sampler node in the trace tree!")
        return None

    @classmethod
    def filter_inputs_by_trace_tree(cls, inputs, trace_tree, prefer_nearest):
        filtered = defaultdict(list)
        for meta, input_list in inputs.items():
            for node_id, input_value in input_list:
                trace = trace_tree.get(node_id)
                if trace:
                    filtered[meta].append((node_id, input_value, trace[0]))

        for key in filtered:
            filtered[key].sort(key=lambda x: x[2], reverse=not prefer_nearest)

        return filtered
