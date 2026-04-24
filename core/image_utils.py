from PIL import Image
import io
import base64

def optimize_base64_image(url_or_b64, max_size=(1024, 1024), quality=80):
    """
    Takes a base64 data URI or raw base64 string, resizes the image while maintaining 
    aspect ratio, compresses it as JPEG, and returns a new data URI.
    This significantly reduces token payload sizes and proxy latency for LLMs.
    """
    try:
        prefix = "data:image/jpeg;base64,"
        b64_string = url_or_b64
        
        if url_or_b64.startswith("data:"):
            parts = url_or_b64.split(",", 1)
            if len(parts) == 2:
                b64_string = parts[1]
                
        img_data = base64.b64decode(b64_string)
        img = Image.open(io.BytesIO(img_data))
        
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        # Qwen models reject images smaller than 10x10. We enforce a minimum of 15x15.
        min_size = 15
        if img.width < min_size or img.height < min_size:
            ratio = max(min_size / img.width, min_size / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            
        # Resize using thumbnail (maintains aspect ratio, modifies in-place, only downscales)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=quality)
        
        optimized_b64 = base64.b64encode(out.getvalue()).decode("utf-8")
        return prefix + optimized_b64
        
    except Exception as e:
        print(f"[Image Optimizer Error] {e}")
        # Return original if parsing fails
        if not url_or_b64.startswith("data:"):
            return "data:image/jpeg;base64," + url_or_b64
        return url_or_b64
