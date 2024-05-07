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
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"image": ("IMAGE", {})}}
    
    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE")
    RETURN_NAMES = ("Red Channel", "Green Channel", "Blue Channel", "Luminosity Histogram", "RGB Histogram")
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
        red_hist = np.histogram(image_np[:, :, 0], bins=256, range=(0, 255))[0]
        green_hist = np.histogram(image_np[:, :, 1], bins=256, range=(0, 255))[0]
        blue_hist = np.histogram(image_np[:, :, 2], bins=256, range=(0, 255))[0]

        # Calculate luminosity histogram
        luminosity = 0.2989 * image_np[:, :, 0] + 0.5870 * image_np[:, :, 1] + 0.1140 * image_np[:, :, 2]
        lum_hist = np.histogram(luminosity, bins=256, range=(0, 255))[0]

        def hist_to_image(hist, color):
            fig, ax = plt.subplots()
            ax.fill_between(range(256), 0, hist, color=color, step='mid', alpha=0.7)
            ax.set_facecolor("white")
            ax.axis('off')
            fig.patch.set_visible(False)
            fig.canvas.draw()

            # Convert plot to a numpy array
            data = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
            data = data.reshape(fig.canvas.get_width_height()[::-1] + (3,))
            plt.close(fig)
            return torch.tensor(data).permute(2, 0, 1).float() / 255

        # Generate images for each channel with respective colors
        red_image = hist_to_image(red_hist, 'red')
        green_image = hist_to_image(green_hist, 'green')
        blue_image = hist_to_image(blue_hist, 'blue')
        lum_image = hist_to_image(lum_hist, 'gray')

        # Create RGB Histogram by overlaying each color histogram
        composite_fig, composite_ax = plt.subplots()
        for hist, color in zip([red_hist, green_hist, blue_hist], ['red', 'green', 'blue']):
            composite_ax.fill_between(range(256), 0, hist, color=color, alpha=0.5, step='mid')
        composite_ax.set_facecolor("white")
        composite_ax.axis('off')
        composite_fig.patch.set_visible(False)
        composite_fig.canvas.draw()

        composite_data = np.frombuffer(composite_fig.canvas.tostring_rgb(), dtype=np.uint8)
        composite_data = composite_data.reshape(composite_fig.canvas.get_width_height()[::-1] + (3,))
        plt.close(composite_fig)
        rgb_image = torch.tensor(composite_data).permute(2, 0, 1).float() / 255

        return red_image, green_image, blue_image, lum_image, rgb_image

# No additional configuration needed here since class and display mappings are handled separately.
