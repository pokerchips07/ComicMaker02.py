"""
make_graphic_novel.py
Python script to build simple graphic-novel pages (PNG) and export as a PDF.

Features:
- Create panels from image files or color placeholders
- Arrange panels into a page grid (flexible layout)
- Add caption/speech bubbles with wrapped text and tails
- Export pages (PNG) and a combined PDF

Dependencies:
    pip install pillow

Usage:
    Edit the `example()` function at bottom with your panels and text, then run:
        python make_graphic_novel.py
"""

from PIL import Image, ImageDraw, ImageFont
import textwrap
import os
from typing import List, Tuple, Optional

# ---------- Config ----------
PAGE_WIDTH = 2480   # pixels (approx A4 at 300 dpi)
PAGE_HEIGHT = 3508
PAGE_BG = (255, 255, 255)
DEFAULT_FONT_SIZE = 36
FONT_PATH = None  # set to a path like "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# ---------- Utility ----------

def load_font(size=DEFAULT_FONT_SIZE):
    if FONT_PATH and os.path.isfile(FONT_PATH):
        return ImageFont.truetype(FONT_PATH, size)
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()

def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    """Wrap text to fit max_width using font metrics."""
    words = text.split()
    lines = []
    if not words:
        return lines
    line = words[0]
    for w in words[1:]:
        test = line + " " + w
        wbox = font.getbbox(test)
        wwidth = wbox[2] - wbox[0]
        if wwidth <= max_width:
            line = test
        else:
            lines.append(line)
            line = w
    lines.append(line)
    return lines

# ---------- Panel creation ----------

def create_panel_from_image(image_path: str, target_size: Tuple[int,int]) -> Image.Image:
    """Open an image and fit it into target_size while preserving aspect ratio."""
    img = Image.open(image_path).convert("RGBA")
    img.thumbnail(target_size, Image.LANCZOS)
    w, h = img.size
    canvas = Image.new("RGBA", target_size, (255,255,255,0))
    canvas.paste(img, ((target_size[0]-w)//2, (target_size[1]-h)//2), mask=img)
    return canvas

def create_placeholder_panel(color: Tuple[int,int,int], target_size: Tuple[int,int], label: Optional[str]=None) -> Image.Image:
    """Create a colored placeholder panel, optionally with a centered label."""
    img = Image.new("RGBA", target_size, color + (255,))
    if label:
        draw = ImageDraw.Draw(img)
        font = load_font(int(min(target_size)/10))
        lines = textwrap.wrap(label, width=20)
        y = (target_size[1] - len(lines) * (font.getbbox("Ay")[3] - font.getbbox("Ay")[1])) // 2
        for line in lines:
            bbox = font.getbbox(line)
            w = bbox[2] - bbox[0]
            draw.text(((target_size[0]-w)//2, y), line, fill=(255,255,255), font=font)
            y += (bbox[3] - bbox[1])
    return img

# ---------- Speech/Captions ----------

def draw_round_rect(draw: ImageDraw.Draw, xy, radius, fill, outline=None, outline_width=2):
    """Draw a rounded rectangle (Pillow doesn't have it built-in for all versions)."""
    x0,y0,x1,y1 = xy
    # corners as pieslices
    draw.pieslice([x0, y0, x0+2*radius, y0+2*radius], 180, 270, fill=fill)
    draw.pieslice([x1-2*radius, y0, x1, y0+2*radius], 270, 0, fill=fill)
    draw.pieslice([x0, y1-2*radius, x0+2*radius, y1], 90, 180, fill=fill)
    draw.pieslice([x1-2*radius, y1-2*radius, x1, y1], 0, 90, fill=fill)
    # rectangles
    draw.rectangle([x0+radius, y0, x1-radius, y1], fill=fill)
    draw.rectangle([x0, y0+radius, x1, y1-radius], fill=fill)
    if outline:
        # approximate outline by drawing slightly smaller rounded rect in outline color
        draw_round_rect(draw, (x0+outline_width, y0+outline_width, x1-outline_width, y1-outline_width), max(0, radius-outline_width), fill=None, outline=None)

def add_text_bubble(
    page: Image.Image,
    text: str,
    bubble_box: Tuple[int,int,int,int],
    tail_coords: Tuple[Tuple[int,int], Tuple[int,int]],
    font: Optional[ImageFont.FreeTypeFont] = None,
    bubble_fill=(255,255,255,230),
    bubble_outline=(0,0,0),
    padding=16,
    radius=20
):
    """Add a rounded speech/caption bubble with a triangular tail."""
    if font is None:
        font = load_font(DEFAULT_FONT_SIZE)
    draw = ImageDraw.Draw(page)
    x0,y0,x1,y1 = bubble_box
    # draw tail triangle (two points forming base and one tip)
    (bx,by),(tx,ty) = tail_coords  # base point, tip point
    # tail as polygon: small base square to triangle - simple
    tail = [(bx,by), (tx,ty), (bx+ (tx-bx)//2, by)]
    draw.polygon(tail, fill=bubble_fill)
    # draw rounded rect
    draw_round_rect(draw, (x0,y0,x1,y1), radius=radius, fill=bubble_fill, outline=bubble_outline)
    # draw outline - simple rectangle border (we've approximated above)
    # wrap text inside bubble
    max_text_width = (x1 - x0) - 2*padding
    lines = wrap_text(text, font, max_text_width)
    line_h = font.getbbox("Ay")[3] - font.getbbox("Ay")[1]
    total_h = len(lines) * line_h
    # starting y
    ty_start = y0 + padding
    for i, line in enumerate(lines):
        bbox = font.getbbox(line)
        w = bbox[2] - bbox[0]
        draw.text((x0 + padding, ty_start + i*line_h), line, fill=(0,0,0), font=font)

# ---------- Page layout ----------

def layout_panels_on_page(
    panels: List[Image.Image],
    page_size: Tuple[int,int] = (PAGE_WIDTH, PAGE_HEIGHT),
    margin: int = 80,
    gutter: int = 20,
    grid: Tuple[int,int] = (2,3),  # columns, rows
    panel_bg=(0,0,0)
) -> Image.Image:
    """Arrange panels into a grid. panels length should be <= cols*rows.
    Panels will be scaled to fit their cell while preserving aspect ratio.
    """
    cols, rows = grid
    pw = (page_size[0] - 2*margin - (cols-1)*gutter) // cols
    ph = (page_size[1] - 2*margin - (rows-1)*gutter) // rows
    page = Image.new("RGBA", page_size, PAGE_BG + (255,))
    idx = 0
    for r in range(rows):
        for c in range(cols):
            if idx >= len(panels):
                break
            panel = panels[idx]
            # resize/pad panel to cell
            panel_thumb = panel.copy()
            panel_thumb.thumbnail((pw,ph), Image.LANCZOS)
            cell_x = margin + c*(pw+gutter) + (pw - panel_thumb.width)//2
            cell_y = margin + r*(ph+gutter) + (ph - panel_thumb.height)//2
            # optional border
            border = Image.new("RGBA", (panel_thumb.width+8, panel_thumb.height+8), (0,0,0,0))
            # paste onto page
            page.paste(panel_thumb, (cell_x, cell_y), panel_thumb)
            idx += 1
    return page.convert("RGB")

# ---------- Export ----------

def save_pages_as_images(pages: List[Image.Image], out_dir: str, basename="page"):
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for i, p in enumerate(pages, start=1):
        path = os.path.join(out_dir, f"{basename}_{i:02d}.png")
        p.save(path, "PNG")
        paths.append(path)
    return paths

def save_pages_to_pdf(pages: List[Image.Image], out_pdf_path: str):
    # Ensure all pages are RGB
    imgs = [p.convert("RGB") for p in pages]
    if not imgs:
        raise ValueError("No pages to save")
    first, rest = imgs[0], imgs[1:]
    first.save(out_pdf_path, "PDF", save_all=True, append_images=rest)
    return out_pdf_path

# ---------- Example / Demo ----------

def example():
    """Create a short 3-page mini-graphic using placeholders and some real images (if provided)."""
    # Example panels: either image paths or placeholders (color,label)
    # Replace the placeholder panels with create_panel_from_image("path/to/image.png", (pw,ph))
    placeholder_panels = [
        create_placeholder_panel((85, 107, 47), (1200, 900), "Monty at desk"),
        create_placeholder_panel((50, 90, 150), (1200, 900), "Py the snake"),
        create_placeholder_panel((180, 60, 60), (1200, 900), "print(\"Hello, world!\")"),
        create_placeholder_panel((200, 180, 60), (1200, 900), "Treasure Boxes"),
        create_placeholder_panel((70, 160, 140), (1200, 900), "Forked Roads"),
        create_placeholder_panel((120, 70, 190), (1200, 900), "Toolbox: functions"),
    ]

    # Layout: 2 columns x 3 rows per page -> 6 panels per page
    page = layout_panels_on_page(placeholder_panels, grid=(2,3))
    draw = ImageDraw.Draw(page)
    # Add a couple of bubbles
    font = load_font(30)
    add_text_bubble(
        page,
        "Monty wanted to learn. Py slithered in.",
        bubble_box=(200, 200, 1000, 360),
        tail_coords=((800,360),(900,420)),
        font=font
    )
    add_text_bubble(
        page,
        "print(\"Hello, world!\")",
        bubble_box=(1480, 2200, 2360, 2360),
        tail_coords=((2000,2360),(1900,2500)),
        font=load_font(28),
        bubble_fill=(255,255,204,230)
    )

    # Create second page (simpler)
    panels_page2 = [
        create_placeholder_panel((110, 110, 200), (1200,900), "If / Else"),
        create_placeholder_panel((200, 110, 110), (1200,900), "For / While"),
    ]
    page2 = layout_panels_on_page(panels_page2, grid=(2,1))
    add_text_bubble(page2, "Decisions shape the story", (120,120,920,240), ((500,240),(420,320)), font=load_font(28))

    # Third page (classes)
    panels_page3 = [
        create_placeholder_panel((60,140,60), (1200,900), "Classes & Blueprints"),
    ]
    page3 = layout_panels_on_page(panels_page3, grid=(1,1))
    add_text_bubble(page3, "Bundle data + behavior with classes", (140,80,1200,200), ((500,200),(560,300)), font=load_font(28))

    pages = [page, page2, page3]
    out_dir = "out_pages"
    image_paths = save_pages_as_images(pages, out_dir)
    print("Saved page images:", image_paths)
    pdf_path = "graphic_novel_demo.pdf"
    save_pages_to_pdf(pages, pdf_path)
    print("Saved PDF:", pdf_path)

if __name__ == "__main__":
    example()