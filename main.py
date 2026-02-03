import os
import shutil
import subprocess
import tempfile
from fastapi import FastAPI, UploadFile, File, Header, HTTPException
from fastapi.responses import FileResponse

app = FastAPI()

API_KEY = os.getenv("API_KEY", "")  # pon una key para proteger el endpoint
DPI = int(os.getenv("DPI", "300"))  # 200–300 suele ir perfecto en facturas

@app.post("/pdf-to-png")
async def pdf_to_png(
    file: UploadFile = File(...),
    x_api_key: str | None = Header(default=None)
):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail=f"Unsupported content-type: {file.content_type}")

    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = os.path.join(tmp, "in.pdf")
        out_prefix = os.path.join(tmp, "page")

        with open(pdf_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # 1 página: -f 1 -l 1
        cmd = ["pdftoppm", "-png", "-r", str(DPI), "-f", "1", "-l", "1", pdf_path, out_prefix]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            raise HTTPException(status_code=500, detail=f"pdftoppm failed: {e.stderr.decode('utf-8', 'ignore')[:500]}")

        png_path = out_prefix + "-1.png"
        if not os.path.exists(png_path):
            raise HTTPException(status_code=500, detail="PNG not generated")

        return FileResponse(
            png_path,
            media_type="image/png",
            filename=(file.filename or "invoice.pdf").rsplit(".", 1)[0] + ".png"
        )

@app.get("/health")
def health():
    return {"ok": True}
