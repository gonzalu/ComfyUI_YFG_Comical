import numpy as np
import cv2
import matplotlib.pyplot as plt
import torch

class ImageHistogram_v1:
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
        if image.size(2) == 3:  # Correct order of dimensions (height, width, channels)
            image_np = image.cpu().numpy()  # No need to permute
        else:
            raise ValueError("Unsupported image format with shape: {}".format(image.shape))

        image_np = (image_np * 255).astype(np.uint8)

        # Handle grayscale images by replicating the channels if only one channel is present
        if image_np.shape[2] == 1:
            image_np = np.repeat(image_np, 3, axis=2)

        # Split the channels
        channels = cv2.split(image_np)

        # Define a function to convert histogram to image using plt
        def hist_to_image(hist, color):
            plt.figure()
            plt.hist(hist, bins=256, range=(0, 256), color=color, alpha=0.7)
            plt.axis('off')
            plt.gca().set_facecolor('white')
            plt.gcf().set_size_inches(4, 4)
            plt.gcf().canvas.draw()

            # Convert plot to numpy array
            data = np.frombuffer(plt.gcf().canvas.tostring_rgb(), dtype=np.uint8)
            data = data.reshape(plt.gcf().canvas.get_width_height()[::-1] + (3,))
            plt.close()
            return torch.tensor(data).permute(2, 0, 1).float() / 255

        # Generate images for each channel with respective colors
        red_image = hist_to_image(channels[2].ravel(), 'red')
        green_image = hist_to_image(channels[1].ravel(), 'green')
        blue_image = hist_to_image(channels[0].ravel(), 'blue')

        # Calculate luminosity using the NTSC conversion formula
        luminosity = 0.2989 * channels[2] + 0.5870 * channels[1] + 0.1140 * channels[0]
        lum_image = hist_to_image(luminosity.ravel(), 'gray')

        # Create RGB Histogram by overlaying each color histogram
        plt.figure()
        for hist, color in zip([channels[2].ravel(), channels[1].ravel(), channels[0].ravel()], ['red', 'green', 'blue']):
            plt.hist(hist, bins=256, range=(0, 256), color=color, alpha=0.5)
        plt.axis('off')
        plt.gca().set_facecolor('white')
        plt.gcf().set_size_inches(4, 4)
        plt.gcf().canvas.draw()

        composite_data = np.frombuffer(plt.gcf().canvas.tostring_rgb(), dtype=np.uint8)
        composite_data = composite_data.reshape(plt.gcf().canvas.get_width_height()[::-1] + (3,))
        plt.close()
        rgb_image = torch.tensor(composite_data).permute(2, 0, 1).float() / 255

        return red_image, green_image, blue_image, lum_image, rgb_image

# No additional configuration needed here since class and display mappings are handled separately.