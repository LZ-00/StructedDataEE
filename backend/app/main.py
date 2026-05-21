from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, dashboard, distillation, evaluation, extraction, finetune, models

app = FastAPI(title="激光焊接结构化数据抽取与质量评估系统 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(extraction.router, prefix="/api/extraction", tags=["extraction"])
app.include_router(evaluation.router, prefix="/api/evaluation", tags=["evaluation"])
app.include_router(distillation.router, prefix="/api/distillation", tags=["distillation"])
app.include_router(finetune.router, prefix="/api/finetune", tags=["finetune"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(models.router, prefix="/api/models", tags=["models"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
