from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from datetime import datetime

from database.db import readings_col
from auth.dependencies import get_current_user
from services.report_service import rows_to_csv, rows_to_excel, rows_to_pdf

router = APIRouter(prefix="/api/reports", tags=["reports"])


async def _fetch_rows(building_id: str | None, date_from: str | None, date_to: str | None):
    query = {}
    if building_id:
        query["buildingID"] = building_id
    time_query = {}
    if date_from:
        time_query["$gte"] = datetime.fromisoformat(date_from)
    if date_to:
        time_query["$lte"] = datetime.fromisoformat(date_to)
    if time_query:
        query["timestamp"] = time_query

    rows = await readings_col.find(query).sort("timestamp", -1).to_list(5000)
    for r in rows:
        r["_id"] = str(r["_id"])
        r["timestamp"] = r["timestamp"].isoformat() if isinstance(r.get("timestamp"), datetime) else r.get("timestamp")
    return rows


@router.get("/csv")
async def report_csv(
    buildingID: str = Query(default=None),
    from_: str = Query(default=None, alias="from"),
    to: str = Query(default=None),
    user: dict = Depends(get_current_user),
):
    rows = await _fetch_rows(buildingID, from_, to)
    content = rows_to_csv(rows)
    return Response(content=content, media_type="text/csv",
                     headers={"Content-Disposition": "attachment; filename=shm-report.csv"})


@router.get("/excel")
async def report_excel(
    buildingID: str = Query(default=None),
    from_: str = Query(default=None, alias="from"),
    to: str = Query(default=None),
    user: dict = Depends(get_current_user),
):
    rows = await _fetch_rows(buildingID, from_, to)
    content = rows_to_excel(rows)
    return Response(content=content, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     headers={"Content-Disposition": "attachment; filename=shm-report.xlsx"})


@router.get("/pdf")
async def report_pdf(
    buildingID: str = Query(default=None),
    from_: str = Query(default=None, alias="from"),
    to: str = Query(default=None),
    user: dict = Depends(get_current_user),
):
    rows = await _fetch_rows(buildingID, from_, to)
    title = f"S-SHM Readings Report{' — ' + buildingID if buildingID else ''}"
    content = rows_to_pdf(rows, title=title)
    return Response(content=content, media_type="application/pdf",
                     headers={"Content-Disposition": "attachment; filename=shm-report.pdf"})
