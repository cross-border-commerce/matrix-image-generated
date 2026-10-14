PLACEMENT_LABELS = {
    "chest_center": "胸前",
}

SYSTEM_PROMPT = (
    "你是一名服装电商商品图生成助手。"
    "根据用户提供的商品信息与图片需求，编写清晰、具体、适用于图像生成模型的提示词。"
    "重点描述服装款式、颜色、面料、版型、细节、模特或平铺方式、背景、构图、光线和拍摄风格。"
    "优先保证商品外观准确，不擅自添加用户未提及的品牌、图案、配饰或设计细节。若信息不足，采用简洁、常见的电商摄影设定；"
    "默认生成干净、真实、突出商品的商业摄影效果，并避免文字、水印、变形肢体和不合理的服装结构，不要出现任何品牌标识或店铺标识。"
)

IMAGE_PROMPT_TEMPLATE = (
    "第一张参考图是工厂纯色实拍商品图。"
    "第二张参考图是印花 logo。"
    "生成电商服装商品主图。把印花logo图案自然合成到服装{placement}，"
    "贴合面料褶皱、光影和透视，保持原服装颜色与质感，干净背景，适合详情页主图。"
)


def render_image_prompt(placement: str) -> str:
    label = PLACEMENT_LABELS.get(placement, placement)
    return IMAGE_PROMPT_TEMPLATE.format(placement=label)
