from PIL import Image, ImageDraw, ImageFont
import textwrap

def generate_caption_image(text, out_path):
    W, H = 1088, 1920
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    
    font_size = 56
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    except Exception:
        font = ImageFont.load_default()
    
    lines = textwrap.wrap(text, width=28)
    line_spacing = int(font_size * 1.5)
    total_height = len(lines) * line_spacing
    
    y = int(H * 0.83) - total_height // 2
    
    # Calculate bounding box
    max_w = 0
    for line in lines:
        left, top, right, bottom = d.textbbox((0, 0), line, font=font)
        max_w = max(max_w, right - left)
    
    padding = 30
    box_x0 = (W - max_w) // 2 - padding
    box_y0 = y - padding
    box_x1 = (W + max_w) // 2 + padding
    box_y1 = y + total_height + padding
    
    # Draw semi-transparent box
    d.rectangle([box_x0, box_y0, box_x1, box_y1], fill=(0, 0, 0, 160))
    
    current_y = y
    for line in lines:
        left, top, right, bottom = d.textbbox((0, 0), line, font=font)
        w = right - left
        x = (W - w) // 2
        # Drop shadow
        d.text((x + 3, current_y + 3), line, font=font, fill=(0, 0, 0, 255))
        # Text
        d.text((x, current_y), line, font=font, fill=(255, 255, 255, 255))
        current_y += line_spacing
        
    img.save(out_path)

generate_caption_image("Nifty IT suffers worst monthly fall since 2008!", "caption_test.png")
