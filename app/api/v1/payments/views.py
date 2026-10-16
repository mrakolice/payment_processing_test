import fastapi

router = fastapi.APIRouter(prefix="/payments", tags=["payments"])

@router.post('/')
async def create_payment():
    return ''

@router.get('/{payment_id')
async def get_payment(payment_id: str):
    return ''
