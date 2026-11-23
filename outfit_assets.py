"""圖片名稱與路徑集中管理。路徑相對於專案的 static/ 目錄。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class OutfitAsset:
    title: str
    path: str


OUTFITS = {
    "hot": OutfitAsset("透氣短袖穿搭", "images/outfits/hot.svg"),
    "mild": OutfitAsset("輕薄休閒穿搭", "images/outfits/mild.svg"),
    "layered": OutfitAsset("洋蔥式穿搭", "images/outfits/layered.svg"),
    "cold": OutfitAsset("防風保暖穿搭", "images/outfits/cold.svg"),
}

ACCESSORIES = {
    "raincoat": OutfitAsset("兩件式雨衣", "images/outfits/raincoat.svg"),
    "umbrella": OutfitAsset("折疊傘", "images/outfits/umbrella.svg"),
    "jacket": OutfitAsset("薄外套", "images/outfits/jacket.svg"),
    "sun": OutfitAsset("防曬帽／墨鏡", "images/outfits/sun.svg"),
    "windbreaker": OutfitAsset("防風外套", "images/outfits/windbreaker.svg"),
    "shoes": OutfitAsset("好走的鞋", "images/outfits/shoes.svg"),
    "water": OutfitAsset("水壺", "images/outfits/water.svg"),
}
