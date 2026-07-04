import os
import logging
import uuid
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import UPLOAD_DIR, OUTPUT_DIR
from ingestion import extract_text_from_upload
from analysis import suggest_headings, generate_slide_content, generate_search_queries
from search import search_images, download_and_convert
from pptgen import generate_pptx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Presentation Maker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    content: str

class SlideData(BaseModel):
    heading: str
    bullets: list[str] = []

class GenerateRequest(BaseModel):
    title: str
    slides: list[SlideData]
    content: str = ""


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/ingest")
async def ingest(
    text: str = Form(""),
    files: list[UploadFile] = File(default=[]),
):
    extracted = []
    if text.strip():
        extracted.append(text.strip())
    for f in files:
        try:
            content = await f.read()
            file_text = await extract_text_from_upload(content, f.filename or "")
            if file_text:
                extracted.append(file_text)
        except Exception as e:
            logger.error(f"Failed to process {f.filename}: {e}")
    if not extracted:
        raise HTTPException(status_code=400, detail="No content provided")
    return {"content": "\n\n".join(extracted)}


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="No content to analyze")
    headings = await suggest_headings(req.content)
    if not headings:
        raise HTTPException(status_code=500, detail="Failed to generate headings")
    return {"headings": headings}


@app.post("/api/generate")
async def generate(req: GenerateRequest):
    if not req.slides:
        raise HTTPException(status_code=400, detail="No slides provided")
    slides_data = []
    for i, slide in enumerate(req.slides):
        logger.info(f"Generating slide {i+1}/{len(req.slides)}: {slide.heading}")
        bullets = slide.bullets
        if not bullets:
            bullets = await generate_slide_content(slide.heading, req.content)
        image_bytes = None
        queries = await generate_search_queries(slide.heading, bullets)
        for q in queries:
            results = await search_images(q)
            if results:
                img_bytes = await download_and_convert(results[0]["url"])
                if img_bytes:
                    image_bytes = img_bytes
                    break
        slides_data.append({
            "heading": slide.heading,
            "bullets": bullets,
            "image_bytes": image_bytes,
        })
    pptx_bytes = await generate_pptx(req.title, slides_data)
    filename = f"{uuid.uuid4().hex[:12]}.pptx"
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(pptx_bytes)
    return FileResponse(
        filepath,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename="presentation.pptx",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
