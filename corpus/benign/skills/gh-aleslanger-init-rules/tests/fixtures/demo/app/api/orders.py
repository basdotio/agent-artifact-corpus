from fastapi import APIRouter, Depends, Header, HTTPException
from app.auth import current_user
from app.db.session import Session
from app.db.models import Order
router = APIRouter()
def user(authorization: str = Header()) -> str:
    return current_user(authorization.removeprefix("Bearer "))
@router.get("/orders/{order_id}")
def get_order(order_id: str, uid: str = Depends(user)):
    with Session() as s:
        o = s.get(Order, order_id)
        if o is None or o.owner_id != uid:
            raise HTTPException(404)
        return {"id": o.id, "amount_cents": o.amount_cents, "status": o.status}
@router.post("/orders/{order_id}/pay")
def pay(order_id: str, uid: str = Depends(user)):
    with Session() as s, s.begin():
        o = s.get(Order, order_id)
        if o is None or o.owner_id != uid:
            raise HTTPException(404)
        if o.status == "paid":
            return {"status": "paid"}
        o.status = "paid"
    return {"status": "paid"}
