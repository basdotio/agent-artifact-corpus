# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import logging
import os
import textwrap

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

DEFAULT_OUTPUT_PATH = "timeline.png"
ICON_FONT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "fonts",
    "Segoe Fluent Icons.ttf"
)
ICON_FONT = fm.FontProperties(fname=ICON_FONT_PATH, size=12)

# https://learn.microsoft.com/en-us/windows/apps/design/style/segoe-fluent-icons-font
ICON_MAPPINGS = {
    "biopsy": "\ue924",         # Annotation
    "diagnosis": "\ue9d9",      # Diagnostic
    "imaging": "\ue8b8",        # Webcam
    "radiation": "\ue8b8",      # Webcam
    "chemotherapy": "\uf196",   # Beaker
    "cytology": "\ue9f9",
    "immunotherapy": "\ue9f9",
    "procedure": "\ue9f9",
    "treatment": "\ue9f9",
    "report": "\ue77f",         # Paste
    "scan": "\ue8b8",           # Webcam
    "surgery": "\ue8c6",        # Cut
    "visit": "\ue731",          # EMI
    "x-ray": "\ue8b8",          # Webcam
}

logger = logging.getLogger(__name__)


def _calc_entry_height(
    entry: dict, summary_height: float = 0.12, summary_width: int = 36, title_height: float = 0.25
) -> float:
    """
    Calculate the height of a single entry in the timeline.

    Args:
        entry (dict): The entry data containing note_summary.
        summary_height (float): Height of each line of text in inches.
        summary_width (int): Maximum number of characters per line.
        title_height (float): Height of the title in inches.

    Returns:
        float: The height of the entry in inches.
    """
    content = entry.get("note_summary", "")
    content_rows = len(textwrap.wrap(content, summary_width))
    content_height = content_rows * summary_height

    return content_height + title_height


def _calc_total_height(timeline: list[dict], margin_top: float = 0.2, margin_bottom: float = 0.2) -> float:
    """
    Calculate the total height of the timeline based on the entries.

    Args:
        timeline (list[dict]): List of entries in the timeline.
        margin_top (float): Top margin height.
        margin_bottom (float): Bottom margin height.

    Returns:
        float: Total height of the timeline.
    """
    total_height = margin_top + margin_bottom

    for entry in timeline:
        total_height += _calc_entry_height(entry)

    return total_height


def _get_icon(note_type: str) -> str:
    for keyword, icon in ICON_MAPPINGS.items():
        if keyword in note_type:
            return icon
    return "\ue9f9"  # ReportDocument


def _format_title(note_title: str) -> str:
    if len(note_title) > 28:
        return note_title[:28] + "\u2026"   # append ellipsis
    return note_title


def create_timeline_image(
    timeline: list[dict], width: float = 3.4, font_size: int = 8, font_color: str = "black",
    icon_offset: float = 0.2, margin_top: float = 0.2, output_path: str = DEFAULT_OUTPUT_PATH
) -> None:
    """
    Create a timeline image from a list of entries.

    Args:
        timeline (list[dict]): List of entries in the timeline.
        width (float): Width of the output image (in inches).
        font_size (int): Font size for the text.
        font_color (str): Font color for the text.
        icon_offset (float): Horizontal offset for the title when an icon is used.
        margin_top (float): Top margin height in inches.
        output_path (str): Path to save the output image.
    """
    # Calculate total vertical space
    total_height = _calc_total_height(timeline)

    # Create the figure using the specified width and calculated height
    fig, ax = plt.subplots(figsize=(width, total_height))

    # Draw the central vertical timeline line from y=0 to y=total_height at x=0
    ax.plot([0, 0], [0, total_height], color=font_color, lw=2)

    # Starting y-coordinate (from the top)
    current_y = total_height - margin_top
    # x-coordinate where horizontal connector lines end (and event text begins)
    connector_x = 0.3

    for entry in timeline:
        time_label = entry.get("date", "yyyy-mm-dd")
        content = entry.get("note_summary", "No content available.")
        title = _format_title(entry.get("note_title", "Unspecified"))
        note_type = entry.get("note_type", "")
        icon = _get_icon(note_type.lower())

        entry_height = _calc_entry_height(entry)

        date_y = current_y
        entry_y = current_y + 0.05

        # Display the time stamp label to the left of the timeline (in color #0a6dc2)
        ax.text(-0.1, date_y, time_label,
                horizontalalignment='right', verticalalignment='center',
                fontsize=font_size, fontweight='bold', color="#0a6dc2")

        # The connector attaches at the top of the event block (current_y)
        connector_y = current_y

        # Draw a horizontal connector from the timeline (x=0) to (connector_x, connector_y)
        ax.plot([0, connector_x], [connector_y, connector_y], color=font_color, lw=1)

        # Draw the icon
        ax.text(connector_x + 0.05, entry_y, icon,
                horizontalalignment='left', verticalalignment='top',
                fontsize=font_size, fontweight='bold', fontproperties=ICON_FONT,
                color="#0a6dc2")

        # Draw the title text offset to the right by icon_offset
        ax.text(connector_x + icon_offset, entry_y, " "+title,
                horizontalalignment='left', verticalalignment='top',
                fontsize=font_size, fontweight='bold', color=font_color)

        # Draw the content just below the title.
        ax.text(connector_x + 0.27, entry_y - 0.14, content,
                horizontalalignment='left', verticalalignment='top',
                fontsize=font_size, color=font_color, wrap=True)

        # Move down for the next event.
        current_y -= entry_height

    # Adjust plot limits and remove axes for a clean look.
    ax.set_xlim(-0.5, width)
    ax.set_ylim(0, total_height)
    ax.axis('off')

    plt.tight_layout()

    # Save the figure to a file
    plt.savefig(output_path, transparent=True)
    plt.close(fig)


def create_timeline_images_by_height(
    timeline: list[dict], height_first: float, height_after: float,
    filename_prefix: str = "timeline", output_path: str = ""
) -> list[str]:
    """
    Create multiple timeline images based on the specified height for the first image and subsequent images.

    Args:
        timeline (list[dict]): List of entries in the timeline.
        height_first (float): Height of the first image in inches.
        height_after (float): Height of subsequent images in inches.
        filename_prefix (str): Prefix for the output filenames.
        output_path (str): Path to save the output images.

    Returns:
        list[str]: List of paths to the generated images.
        """
    if height_first <= 0:
        logger.error(f"Height of the first image is less than or equal to 0: {height_first}. Setting it to 0.")
        height_first = 0
    if height_after <= 0:
        logger.error(f"Height of the subsequent images is less than or equal to 0: {height_after}. Setting it to 0.")
        height_after = 0

    image_paths = []

    def _save_image(entries: list[dict]) -> str:
        image_path = os.path.join(output_path, f"{filename_prefix}{len(image_paths)}.png")
        create_timeline_image(entries, output_path=image_path)
        image_paths.append(image_path)

    is_first = True
    entries = []
    entries_height = 0

    # Batch entries to create timeline images. Each image should be less than the page height of the word document.
    for entry in timeline:
        height = height_first if is_first else height_after

        entries.append(entry)
        entries_height = _calc_total_height(entries)

        # Height has exceeded the target height
        if entries_height >= height:
            # Remove the last entry to meet the target height
            if len(entries) > 1:
                last_entry = entries.pop()
                _save_image(entries)
                entries = [last_entry]
            # Single entry exceeded the target height
            else:
                _save_image(entries)
                entries = []

            # Reset the batch
            is_first = False
            entries_height = _calc_total_height(entries)

    # Save any remaining entries
    if entries:
        _save_image(entries)

    return image_paths


# Enable command line usage
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(
        prog='timeline_image',
        description='Generates a timeline image from a list of events',
        epilog='Text at the bottom of help'
    )
    parser.add_argument('input', help='Path to timeline data')
    parser.add_argument('output', default=DEFAULT_OUTPUT_PATH, nargs='?', help='Path to output image')
    args = parser.parse_args()
    print(args)

    with open(args.input, 'r') as file:
        data = json.load(file)

    create_timeline_images_by_height(data, height_first=5, height_after=7)
