from fastapi import FastAPI, Request
import requests
import pandas as pd
from dotenv import load_dotenv
import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import logging

# 환경 변수 로드
load_dotenv()

# FastAPI 앱 초기화
app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Jinja2 템플릿 설정
templates = Jinja2Templates(directory="templates")

# 환경 변수 설정
API_URL = os.getenv("API_URL")
API_KEY = os.getenv("API_KEY")

# 🔥 로깅 설정 (파일 + 콘솔)
logging.basicConfig(
    level=logging.INFO,  # 로그 레벨 설정
    format="%(asctime)s - %(levelname)s - %(message)s",  # 로그 출력 형식
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),  # 로그를 파일로 저장
        logging.StreamHandler()  # 콘솔에도 출력
    ]
)

logger = logging.getLogger("fastapi_app")

# 🚀 1. CSV 파일 로드하여 노드 & 링크 데이터 매핑 생성
coord_file_path = "../../data/coord/coord_utf.csv"
link_file_path = "../../data/coord/link_utf.csv"

try:
    # 노드 좌표 로드
    df_coord = pd.read_csv(coord_file_path, encoding="utf-8")
    NODE_COORDINATES = {str(row["NODE_ID"]): [row["x"], row["y"]] for _, row in df_coord.iterrows()}
    logger.info("✅ 노드 데이터 로드 완료!")

    # 도로 링크 정보 로드
    df_link = pd.read_csv(link_file_path, encoding="utf-8")
    LINK_INFO = {
        str(row["LINK_ID"]): {
            "start_node": str(row["F_NODE"]),
            "end_node": str(row["T_NODE"]),
            "road_name": row["ROAD_NAME"],
            "max_speed": row["MAX_SPD"],
            "length": row["LENGTH"]
        }
        for _, row in df_link.iterrows()
    }
    logger.info("✅ 도로 링크 데이터 로드 완료!")

except Exception as e:
    logger.error(f"❌ 데이터 로드 실패: {e}")
    NODE_COORDINATES = {}
    LINK_INFO = {}

@app.get("/", response_class=HTMLResponse)
def serve_map(request: Request):
    """
    기본 경로에 접속했을 때 map.html 반환
    """
    logger.info("📌 / 경로에 접근됨 (map.html 렌더링)")
    return templates.TemplateResponse("map.html", {"request": request})

@app.get("/traffic")
def get_traffic_data():
    """
    서울시 ITS API에서 교통 데이터를 가져와 GeoJSON 변환
    """
    logger.info("📡 서울시 ITS API에서 교통 데이터 요청 중...")

    params = {
        "apiKey": API_KEY,
        "type": "all",
        "minX": "126.73",
        "maxX": "127.26",
        "minY": "37.41",
        "maxY": "37.71",
        "getType": "json"
    }
    
    try:
        response = requests.get(API_URL, params=params)
        data = response.json()

        if data["header"]["resultCode"] != 0:
            logger.error("🚨 교통 데이터 요청 실패")
            return {"error": "Failed to fetch traffic data"}

        # 🚀 2. GeoJSON 변환 (링크 ID를 기반으로 노드 간 선(LineString) 생성)
        features = []
        for item in data["body"]["items"]:
            link_id = str(item["linkId"])

            if link_id in LINK_INFO:
                start_id = LINK_INFO[link_id]["start_node"]
                end_id = LINK_INFO[link_id]["end_node"]

                # 노드 ID를 위경도로 변환
                if start_id in NODE_COORDINATES and end_id in NODE_COORDINATES:
                    start_coords = NODE_COORDINATES[start_id]  # [경도, 위도]
                    end_coords = NODE_COORDINATES[end_id]  # [경도, 위도]

                    features.append({
                        "type": "Feature",
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [start_coords, end_coords]
                        },
                        "properties": {
                            "roadName": LINK_INFO[link_id]["road_name"],
                            "speed": float(item["speed"]),
                            "maxSpeed": LINK_INFO[link_id]["max_speed"],
                            "travelTime": float(item["travelTime"]),
                            "length": LINK_INFO[link_id]["length"]
                        }
                    })
            else:
                logger.warning(f"🚨 링크 {link_id}의 도로 정보 없음 (무시됨)")

        logger.info(f"✅ 교통 데이터 변환 완료 (총 {len(features)}개 도로)")
        return {"type": "FeatureCollection", "features": features}

    except Exception as e:
        logger.error(f"❌ 교통 데이터 가져오기 실패: {e}")
        return {"error": "Internal server error"}
