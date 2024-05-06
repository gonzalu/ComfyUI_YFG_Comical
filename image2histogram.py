"""
@author: YFG
@title: YFG Histogram
@nickname: YFG Histogram
@description: This extension calculates the histogram of an image and outputs the results as a graph image.
"""
import numpy as np
import matplotlib.pyplot as plt
import torch

class ImageHistogramNode:
    # Define input and output data types
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"image": ("IMAGE", {})}}
    
    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE")
    RETURN_NAMES = ("Red Channel", "Green Channel", "Blue Channel", "Grayscale Channel", "RGB Histogram")
    FUNCTION = "compute_histograms"
    CATEGORY = "YFG"

    def compute_histograms(self, image):
        # Handling the batch dimension
        if image.dim() == 4:
            image = image[0]  # Process only the first image if in batch

        # Convert torch tensor to numpy array and normalize to [0, 255]
        image_np = image.permute(1, 2, 0).cpu().numpy()
        image_np = (image_np * 255).astype(np.uint8)

        # Calculate histograms for each channel
        red_hist = np.histogram(image_np[:, :, 0], bins=256, range=(0, 256))[0]
        green_hist = np.histogram(image_np[:, :, 1], bins=256, range=(0, 256))[0]
        blue_hist = np.histogram(image_np[:, :, 2], bins=256, range=(0, 256))[0]

        # Calculate grayscale histogram
        gray_image = np.dot(image_np[..., :3], [0.2989, 0.5870, 0.1140])
        gray_hist = np.histogram(gray_image, bins=256, range=(0, 256))[0]

        # Function to convert histogram to smooth image
        def hist_to_image(hist, color):
            fig, ax = plt.subplots()
            ax.fill_between(range(256), 0, hist, color=color, step="mid", alpha=0.6)
            ax.set_facecolor("none")
            ax.axis('off')  # Remove axes
            fig.patch.set_visible(False)
            fig.canvas.draw()
            data = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
            data = data.reshape(fig.canvas.get_width_height()[::-1] + (3,))
            plt.close(fig)
            return torch.tensor(data).permute(2, 0, 1) / 255.0

        # Generate images for each channel
        red_image = hist_to_image(red_hist, 'red')
        green_image = hist_to_image(green_hist, 'green')
        blue_image = hist_to_image(blue_hist, 'blue')
        gray_image = hist_to_image(gray_hist, 'gray')

        # Create RGB Histogram by overlaying each channel histogram
        fig, ax = plt.subplots()
        ax.fill_between(range(256), 0, red_hist, color='red', alpha=0.6)
        ax.fill_between(range(256), 0, green_hist, color='green', alpha=0.6)
        ax.fill_between(range(256), 0, blue_hist, color='blue', alpha=0.6)
        ax.set_facecolor("none")
        ax.axis('off')  # Remove axes
        fig.patch.set_visible(False)
        fig.canvas.draw()
        rgb_data = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
        rgb_data = rgb_data.reshape(fig.canvas.get_width_height()[::-1] + (3,))
        plt.close(fig)
        rgb_image = torch.tensor(rgb_data).permute(2, 0, 1) / 255.0

        return red_image, green_image, blue_image, gray_image, rgb_image


# NODE_CLASS_MAPPINGS = {
    # "image_histogram_node": ImageHistogramNode
# }

# NODE_DISPLAY_NAME_MAPPINGS = {
    # "image_histogram_node": "Image Histogram Generator"
# }