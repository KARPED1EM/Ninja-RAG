"""UI 路由"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["ui"])

# 配置模板
templates = Jinja2Templates(directory="src/ui/templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """聊天界面"""
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/admin", response_class=HTMLResponse)
async def admin(request: Request):
    """管理界面"""
    return templates.TemplateResponse("admin.html", {"request": request})
