@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo    Ninja-RAG 一键启动脚本
echo ========================================
echo.

:: 检查 .env 文件
if not exist .env (
    echo [错误] 未找到 .env 文件
    echo.
    echo 请复制 .env.example 到 .env 并配置参数：
    echo   copy .env.example .env
    echo   然后编辑 .env 填写必要的配置
    echo.
    pause
    exit /b 1
)

:: 检查 Docker Desktop 是否运行
echo [1/4] 检查 Docker Desktop...
docker info >nul 2>&1
if errorlevel 1 (
    echo.
    echo [提示] Docker Desktop 未运行
    echo.
    echo 正在尝试启动 Docker Desktop...

    :: 尝试启动 Docker Desktop
    if exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" (
        start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        echo 等待 Docker Desktop 启动...

        :: 等待 Docker 就绪（最多等待 60 秒）
        set /a timeout=60
        set /a counter=0
        :wait_docker
        timeout /t 2 /nobreak >nul
        docker info >nul 2>&1
        if errorlevel 1 (
            set /a counter+=2
            if !counter! lss !timeout! (
                echo 等待中... (!counter!s/!timeout!s^)
                goto wait_docker
            ) else (
                echo.
                echo [错误] Docker Desktop 启动超时
                echo 请手动启动 Docker Desktop 后重试
                pause
                exit /b 1
            )
        )
        echo Docker Desktop 启动成功！
    ) else (
        echo.
        echo [错误] 未找到 Docker Desktop 安装
        echo 请安装 Docker Desktop 或手动启动后重试
        pause
        exit /b 1
    )
) else (
    echo Docker Desktop 运行正常 ✓
)

echo.
echo [2/4] 检查 Docker 服务...

:: 检查容器是否已运行
docker-compose ps | findstr "Up" >nul 2>&1
if errorlevel 1 (
    echo Docker 服务未启动，正在启动...
    docker-compose up -d

    if errorlevel 1 (
        echo.
        echo [错误] Docker 服务启动失败
        echo 请检查 compose.yml 配置或手动执行 docker-compose up -d
        pause
        exit /b 1
    )

    echo.
    echo 等待服务就绪...
    timeout /t 15 /nobreak >nul
    echo Docker 服务启动成功 ✓
) else (
    echo Docker 服务运行正常 ✓
)

echo.
echo [3/4] 服务信息
echo ========================================
echo.
echo 应用地址: http://localhost:8000
echo 查询界面: http://localhost:8000/
echo 管理界面: http://localhost:8000/admin
echo API 文档: http://localhost:8000/docs
echo.
echo Docker 服务:
echo   MySQL:   localhost:3306
echo   Milvus:  localhost:19530
echo   Neo4j:   http://localhost:7474 (浏览器)
echo            bolt://localhost:7687 (Bolt)
echo.
echo ========================================
echo    提示
echo ========================================
echo.
echo - 按 Ctrl+C 停止服务
echo - 查看 Docker 状态: docker-compose ps
echo - 停止 Docker 服务: docker-compose down
echo.

echo.
echo [4/4] 启动应用服务...
echo.

:: 在当前窗口运行服务
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
