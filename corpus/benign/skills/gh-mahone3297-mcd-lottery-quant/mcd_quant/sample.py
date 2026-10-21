# -*- coding: utf-8 -*-
"""内置样例数据。

**全部是 2026-10-09 从真实麦当劳 MCP 原样抓下来的响应**，字段名、字段值一字未改，
只把积分商城列表里用不到的图片地址、卖点文案裁掉，缩短文件。

所以没配 Token 的人跑 `python run.py`，看到的结论和真机完全一致。
配了 Token 就加 `--live`，直接连线上。
"""

CAPTURED_AT = "2026-10-09"

# ---- query-lottery-info ------------------------------------------------- #
LOTTERY = {
    "activityName": "麦麦积分抽奖",
    "activityStatusText": "进行中",
    "beginTime": "2025-01-26 00:00:00",
    "endTime": "2030-12-31 23:59:59",
    "drawPoint": "24",
    "drawTypeText": "消耗积分抽奖",
    "availablePoint": "0",
    "prizes": [
        {"name": "下单立减3元券", "typeText": "优惠券"},
        {"name": "下单立减2元券", "typeText": "优惠券"},
        {"name": "下单立减1元券", "typeText": "优惠券"},
        {"name": "麦辣三件套5折券", "typeText": "优惠券"},
        {"name": "板烧三件套5折券", "typeText": "优惠券"},
        {"name": "双层鳕鱼三件套6折券", "typeText": "优惠券"},
        {"name": "甜辣小食组合5折券", "typeText": "优惠券"},
        {"name": "小食四件套5.5折券", "typeText": "优惠券"},
        {"name": "麦旋风5折券", "typeText": "优惠券"},
        {"name": "30积分", "typeText": "积分奖"},
    ],
}

# ---- query-my-account --------------------------------------------------- #
ACCOUNT = {
    "availablePoint": "0",
    "accumulativePoint": "267.1",
    "usedPoint": "0",
    "frozenPoint": "0",
    "expiredPoint": "267.1",
    "currentMouthExpirePoint": "0",
    "lastMouthExpirePoint": "0",
    "nextMouthExpirePoint": "0",
}

# ---- query-my-prizes ---------------------------------------------------- #
MY_PRIZES = []

# ---- mall-points-products ----------------------------------------------- #
# 完整 48 条，含已过期的 —— 让「只留现在能换的」这步过滤真的有活干。
MALL = [
    {"spuName": "麦当劳亲子读书会", "spuId": 1830, "point": "0", "price": "45", "upTime": "2023-03-29 00:00:00", "downTime": "2026-12-30 23:59:59", "catName": "读书会", "status": 2},
    {"spuName": "麦当劳奇妙生日派对", "spuId": 1779, "point": "0", "price": "50", "upTime": "2023-03-16 00:00:00", "downTime": "2027-12-31 23:59:59", "catName": "生日类派对", "status": 2},
    {"spuName": "麦当劳一起开心鸭尊享版生日派对", "spuId": 8516, "point": "0", "price": "138", "upTime": "2024-10-31 00:00:00", "downTime": "2026-12-31 23:59:59", "catName": "生日类派对", "status": 2},
    {"spuName": "迪士尼奇妙生日探索之旅", "spuId": 1065, "point": "0", "price": "45", "upTime": "2022-09-22 00:00:00", "downTime": "2026-12-31 23:59:59", "catName": "生日类派对", "status": 2},
    {"spuName": "麦当劳过家家派对尊享版", "spuId": 11308, "point": "0", "price": "118", "upTime": "2025-05-28 00:00:00", "downTime": "2027-12-31 23:59:59", "catName": "主题类派对", "status": 2},
    {"spuName": "万马奔腾开心派对常规版", "spuId": 15276, "point": "0", "price": "58", "upTime": "2026-02-04 00:00:00", "downTime": "2027-06-30 23:49:59", "catName": "主题类派对", "status": 2},
    {"spuName": "四小福永远好朋友派对豪华版", "spuId": 3087, "point": "0", "price": "88", "upTime": "2023-09-27 00:00:00", "downTime": "2027-12-31 23:49:59", "catName": "主题类派对", "status": 2},
    {"spuName": "麦当劳趣读派对2025", "spuId": 10675, "point": "0", "price": "45", "upTime": "2025-04-23 00:00:00", "downTime": "2027-12-31 23:59:59", "catName": "主题类派对", "status": 2},
    {"spuName": "麦当劳海底小纵队欢乐派对（常规版）", "spuId": 17356, "point": "0", "price": "58", "upTime": "2026-07-21 00:00:00", "downTime": "2027-07-15 23:49:59", "catName": "主题类派对", "status": 2},
    {"spuName": "开心特工派对 之 深海探秘", "spuId": 6971, "point": "0", "price": "198", "upTime": "2024-07-05 00:00:00", "downTime": "2026-12-31 23:59:59", "catName": "主题类派对", "status": 2},
    {"spuName": "麦麦奇妙夜捣蛋派对尊享版", "spuId": 13495, "point": "0", "price": "128", "upTime": "2025-10-04 00:00:00", "downTime": "2028-10-04 23:49:59", "catName": "主题类派对", "status": 2},
    {"spuName": "麦当劳过家家派对", "spuId": 6370, "point": "0", "price": "55", "upTime": "2024-05-22 00:00:00", "downTime": "2027-05-22 23:59:59", "catName": "主题类派对", "status": 2},
    {"spuName": "四小福永远好朋友派对常规版", "spuId": 3089, "point": "0", "price": "58", "upTime": "2023-09-27 00:00:00", "downTime": "2027-12-31 23:49:59", "catName": "主题类派对", "status": 2},
    {"spuName": "麦当劳狂欢生日派对 迪士尼疯狂动物城主题（尊享版）", "spuId": 5247, "point": "0", "price": "98", "upTime": "2024-03-28 00:00:00", "downTime": "2026-12-31 23:59:59", "catName": "生日类派对", "status": 2},
    {"spuName": "麦当劳一起开心鸭生日派对", "spuId": 8084, "point": "0", "price": "50", "upTime": "2024-09-27 00:00:00", "downTime": "2026-12-31 23:59:59", "catName": "生日类派对", "status": 2},
    {"spuName": "麦当劳狂欢生日派对 迪士尼疯狂动物城主题", "spuId": 5224, "point": "0", "price": "58", "upTime": "2026-03-03 00:00:00", "downTime": "2026-12-31 23:59:59", "catName": "生日类派对", "status": 2},
    {"spuName": "万马奔腾开心派对尊享版", "spuId": 15279, "point": "0", "price": "138", "upTime": "2026-02-04 00:00:00", "downTime": "2027-06-30 23:49:59", "catName": "主题类派对", "status": 2},
    {"spuName": "麦当劳海底小纵队欢乐派对（尊享版）", "spuId": 17357, "point": "0", "price": "88", "upTime": "2026-07-21 00:00:00", "downTime": "2027-07-15 23:49:59", "catName": "主题类派对", "status": 2},
    {"spuName": "麦麦奇妙夜捣蛋派对常规版", "spuId": 13496, "point": "0", "price": "58", "upTime": "2025-10-04 00:00:00", "downTime": "2028-10-04 23:49:59", "catName": "主题类派对", "status": 2},
    {"spuName": "麦当劳趣读派对", "spuId": 5643, "point": "0", "price": "45", "upTime": "2024-04-23 00:00:00", "downTime": "2027-04-23 23:45:59", "catName": "主题类派对", "status": 2},
    {"spuName": "一年一度品虾会", "spuId": 15146, "point": "0", "price": "25.9", "upTime": "2026-01-23 10:30:00", "downTime": "2026-01-26 23:49:59", "catName": "品鉴会", "status": 2},
    {"spuName": "金拱门板记尝新会", "spuId": 16133, "point": "0", "price": "29.9", "upTime": "2026-04-15 00:00:00", "downTime": "2026-04-20 23:49:59", "catName": "品鉴会", "status": 2},
    {"spuName": "麦咖啡™奶铁品鉴会", "spuId": 1670, "point": "0", "price": "25", "upTime": "2023-02-21 00:00:00", "downTime": "2026-12-31 23:59:59", "catName": "品鉴会", "status": 2},
    {"spuName": "消防体验营", "spuId": 12907, "point": "0", "price": "72", "upTime": "2025-09-01 10:30:00", "downTime": "2026-12-31 23:59:59", "catName": "品鉴会", "status": 2},
    {"spuName": "小小牙医体验营", "spuId": 16158, "point": "0", "price": "72", "upTime": "2026-04-15 14:30:00", "downTime": "2026-12-31 23:49:59", "catName": "品鉴会", "status": 2},
    {"spuName": "职业体验营", "spuId": 12897, "point": "0", "price": "72", "upTime": "2025-09-01 10:30:00", "downTime": "2026-12-31 23:59:59", "catName": "品鉴会", "status": 2},
    {"spuName": "为随心配五大巨星“应援”1积分兑换活动", "spuId": 14931, "point": "1", "price": "0", "upTime": "2026-01-09 10:44:59", "downTime": "2026-01-10 17:00:00", "catName": "到店专用", "status": 2},
    {"spuName": "18.8元2份麦辣鸡翅", "spuId": 6113, "point": "200", "price": "0", "upTime": "2024-12-31 11:45:03", "downTime": "2026-03-21 23:59:59", "catName": "到店专用", "status": 2},
    {"spuName": "10.9元指定小食任选", "spuId": 17077, "point": "200", "price": "0", "upTime": "2026-06-25 00:00:03", "downTime": "2026-12-30 23:59:59", "catName": "到店专用", "status": 2},
    {"spuName": "16.9元麦辣可乐组合", "spuId": 17079, "point": "500", "price": "0", "upTime": "2026-06-25 00:00:03", "downTime": "2026-12-30 23:59:59", "catName": "到店专用", "status": 2},
    {"spuName": "21.9元巨无霸可乐组合", "spuId": 17081, "point": "800", "price": "0", "upTime": "2026-06-25 00:00:03", "downTime": "2026-12-30 23:59:59", "catName": "到店专用", "status": 2},
    {"spuName": "18.8元板烧鸡腿堡两件套", "spuId": 6111, "point": "100", "price": "0", "upTime": "2024-12-31 11:45:00", "downTime": "2026-03-21 23:59:59", "catName": "到店专用", "status": 2},
    {"spuName": "22.8元2份麦辣鸡腿堡", "spuId": 6115, "point": "500", "price": "0", "upTime": "2024-12-31 11:45:03", "downTime": "2026-03-21 23:59:59", "catName": "到店专用", "status": 2},
    {"spuName": "5.9元香芋派/菠萝派任选", "spuId": 15866, "point": "50", "price": "0", "upTime": "2026-03-22 00:00:00", "downTime": "2026-06-24 23:59:59", "catName": "到店专用", "status": 2},
    {"spuName": "28.9元板烧四件套", "spuId": 16052, "point": "800", "price": "0", "upTime": "2026-04-01 00:00:00", "downTime": "2026-06-24 23:59:59", "catName": "到店专用", "status": 2},
    {"spuName": "22.9元2份板烧鸡腿堡", "spuId": 16054, "point": "500", "price": "0", "upTime": "2026-03-31 00:00:00", "downTime": "2026-06-24 23:59:59", "catName": "到店专用", "status": 2},
    {"spuName": "22.9元2份麦辣鸡腿堡", "spuId": 16055, "point": "500", "price": "0", "upTime": "2026-03-31 00:00:03", "downTime": "2026-06-24 23:59:59", "catName": "到店专用", "status": 2},
    {"spuName": "16.9元中薯麦乐鸡组合", "spuId": 16056, "point": "200", "price": "0", "upTime": "2026-04-01 00:00:00", "downTime": "2026-06-24 23:59:59", "catName": "到店专用", "status": 2},
    {"spuName": "罗技键鼠套装", "spuId": 17694, "point": "6666", "price": "0", "upTime": "2026-08-21 14:00:00", "downTime": "2026-08-21 23:59:59", "catName": "玩具", "status": 2},
    {"spuName": "17.9元板烧可乐组合", "spuId": 17080, "point": "500", "price": "0", "upTime": "2026-06-25 00:00:00", "downTime": "2026-12-30 23:59:59", "catName": "到店专用", "status": 2},
    {"spuName": "6.9元可乐麦炫酷", "spuId": 17073, "point": "50", "price": "0", "upTime": "2026-06-25 00:00:03", "downTime": "2026-12-30 23:59:59", "catName": "到店专用", "status": 2},
    {"spuName": "6.9元香芋派/菠萝派任选", "spuId": 17074, "point": "50", "price": "0", "upTime": "2026-06-25 00:00:00", "downTime": "2026-12-30 23:59:59", "catName": "到店专用", "status": 2},
    {"spuName": "10.9元指定小食任选", "spuId": 17076, "point": "100", "price": "0", "upTime": "2026-06-25 00:00:00", "downTime": "2026-12-30 23:59:59", "catName": "到店专用", "status": 2},
    {"spuName": "28.8元巨无霸四件套", "spuId": 5246, "point": "800", "price": "0", "upTime": "2024-03-26 00:00:00", "downTime": "2026-03-21 23:59:59", "catName": "到店专用", "status": 2},
    {"spuName": "18.8元麦辣鸡腿汉堡两件套", "spuId": 6110, "point": "50", "price": "0", "upTime": "2024-12-31 11:45:00", "downTime": "2026-03-21 23:59:59", "catName": "到店专用", "status": 2},
    {"spuName": "18.8元指定小食任选2份", "spuId": 6112, "point": "100", "price": "0", "upTime": "2024-12-31 11:45:03", "downTime": "2026-03-21 23:59:59", "catName": "到店专用", "status": 2},
    {"spuName": "麦麦脆汁鸡两件套", "spuId": 6114, "point": "200", "price": "0", "upTime": "2024-12-31 11:45:00", "downTime": "2026-03-21 23:59:59", "catName": "到店专用", "status": 2},
    {"spuName": "24.8元2份板烧鸡腿堡", "spuId": 6116, "point": "500", "price": "0", "upTime": "2024-12-31 11:45:00", "downTime": "2026-03-21 23:59:59", "catName": "到店专用", "status": 2},
    {"spuName": "Nike Book 2 麦当劳特别联名款", "spuId": 16800, "point": "8888", "price": "0", "upTime": "2026-06-05 14:00:00", "downTime": "2026-06-05 16:00:00", "catName": "鞋袜", "status": 2},
    {"spuName": "9.9元指定小食任选", "spuId": 15867, "point": "100", "price": "0", "upTime": "2026-03-22 00:00:03", "downTime": "2026-06-24 23:59:59", "catName": "到店专用", "status": 2},
]

# ---- campaign-calendar（2026-10-09 当天在跑的活动标题） ------------------- #
CAMPAIGNS_TODAY = [
    "韩式风味蘸酱上新❤️就「酱」心有所「薯」",
    "麦当劳 X PEACEMINUSONE",
    "麦当劳联动G-DRAGON",
    "🫐一口爆汁！蓝莓爆爆珠麦旋风上新",
    "早餐爆款回归，快来pick你的厚松饼堡！📣",
    "🍫麦咖啡13.9r浓浓黑巧来啦！",
    "麦咖啡一早现磨🥳元气早餐震撼来袭！",
    "🩶灰白撞色，灰焰圆筒酷爽登场",
    "超值𝟗.𝟗元早餐两件套陪你开工啦😋",
    "学生专属！49元150天麦金学期卡💳",
    "过家家派对上线，快来一起解锁梦想职业",
    "“韩”风刮到了四件套~龙焰鸡腿堡来袭！",
    "乐享90分钟高质量亲子时间",
    "快来一起参加麦麦派对吧！",
]
