from fastapi import APIRouter, Query, status

from app.core.database import SessionDep
from app.core.exceptions import AppError
from app.modules.restaurants import service
from app.modules.restaurants.schemas import (
    MenuItemCreate,
    MenuItemRead,
    MenuItemUpdate,
    RestaurantCreate,
    RestaurantListItem,
    RestaurantRead,
    RestaurantUpdate,
)

router = APIRouter(prefix="/restaurants", tags=["restaurants"])
menu_router = APIRouter(prefix="/menu-items", tags=["restaurants"])


@router.post("", response_model=RestaurantRead, status_code=status.HTTP_201_CREATED)
async def create_restaurant(data: RestaurantCreate, session: SessionDep):
    return await service.create_restaurant(session, data)


@router.get("", response_model=list[RestaurantListItem])
async def list_restaurants(
    session: SessionDep,
    lat: float | None = Query(default=None, ge=-90, le=90),
    lng: float | None = Query(default=None, ge=-180, le=180),
    radius_m: float = Query(default=5000, gt=0, le=50_000),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Список ресторанів. Якщо передано lat і lng, то геопошук найближчих у радіусі."""
    if (lat is None) != (lng is None):
        raise AppError("Both lat and lng must be provided for geo search")
    if lat is not None and lng is not None:
        nearby = await service.find_nearby(session, lat, lng, radius_m, limit)
        return [
            RestaurantListItem.model_validate(r).model_copy(update={"distance_m": round(d, 1)})
            for r, d in nearby
        ]
    return await service.list_restaurants(session, limit, offset)


@router.get("/{restaurant_id}", response_model=RestaurantRead)
async def get_restaurant(restaurant_id: int, session: SessionDep):
    return await service.get_restaurant(session, restaurant_id)


@router.patch("/{restaurant_id}", response_model=RestaurantRead)
async def update_restaurant(restaurant_id: int, data: RestaurantUpdate, session: SessionDep):
    return await service.update_restaurant(session, restaurant_id, data)


@router.post(
    "/{restaurant_id}/menu", response_model=MenuItemRead, status_code=status.HTTP_201_CREATED
)
async def add_menu_item(restaurant_id: int, data: MenuItemCreate, session: SessionDep):
    return await service.add_menu_item(session, restaurant_id, data)


@router.get("/{restaurant_id}/menu", response_model=list[MenuItemRead])
async def get_menu(restaurant_id: int, session: SessionDep, only_available: bool = True):
    return await service.get_menu(session, restaurant_id, only_available)


@menu_router.patch("/{item_id}", response_model=MenuItemRead)
async def update_menu_item(item_id: int, data: MenuItemUpdate, session: SessionDep):
    return await service.update_menu_item(session, item_id, data)
