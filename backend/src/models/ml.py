from pydantic import BaseModel, Field, create_model
from typing import Optional
import pandas as pd
import joblib
from pydantic.fields import FieldInfo

from src import config

# Load the final feature list saved earlier
features = joblib.load(fr"{config.ROOT}\ml_models\model_features.pkl")

fields = {
    feature: (Optional[float], Field(default=None))
    for feature in features
}

CreditModelInput = create_model(
    "CreditModelInput",
    **fields
)
for i in CreditModelInput.model_fields.items():
    key: str = i[0]
    val: FieldInfo = i[1]
    print(f"{key}: {val.annotation}")