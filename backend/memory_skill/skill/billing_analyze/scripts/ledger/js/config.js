"use strict";
/* ================================================================
 * 打工人小账本 · 静态配置
 * 分类/细类/消费类型/支付平台配置、通用 SVG 图标、小猪存钱罐插画
 * 字段约定与 backend/.../billing/common.py 保持一致
 * ================================================================ */

/* ========== 分类配置（对齐 common.py） ========== */
/* 消费大类：按"消费目的/场景"划分，大类间互斥 */
var CATEGORY_OPTIONS = [
  "餐饮",    // 正餐、外卖、堂食、食材、零食、饮品
  "交通",    // 公交地铁、打车、加油、停车、大巴、车辆维护
  "住房",    // 居住固定支出：房租、房贷、水电、燃气、物业、维修
  "购物",    // 实物商品：日用消耗、服饰鞋包、数码电子、护肤美妆
  "居家",    // 家居耐用品：家具、家电、装修、家纺、厨具
  "娱乐",    // 精神消费：电影、游戏、旅游、健身、聚会
  "医疗",    // 健康：药品、检查、挂号、牙科
  "通讯",    // 话费、宽带、AI服务
  "其他",    // 兜底：人情红包、教育培训、杂项等
];

/* 消费细类（按大类分组） */
var SUBCATEGORY_OPTIONS = {
  "餐饮": ["外卖", "堂食", "食材", "零食", "饮料", "奶茶咖啡", "酒水"],
  "交通": ["公交地铁", "打车", "加油", "停车", "大巴", "车辆维护"],
  "住房": ["房租", "房贷", "水电", "燃气", "物业", "维修"],
  "购物": ["日用消耗", "服饰鞋包", "数码电子", "护肤美妆"],
  "居家": ["家具", "家电", "装修", "家纺", "厨具"],
  "娱乐": ["电影", "游戏充值", "健身", "旅游", "聚会"],
  "医疗": ["药品", "检查", "挂号", "牙科"],
  "通讯": ["话费", "宽带", "AI服务"],
  "其他": ["人情红包", "教育培训", "杂项"],
};

/* 消费类型 */
var EXPENSE_TYPE_OPTIONS = ["刚性固定", "刚性必要", "弹性支出", "未分类"];

/* 支付平台 */
var PLATFORM_OPTIONS = ["微信", "支付宝", "银行卡", "现金", "其他"];

/* 收支类型 */
var DIRECTION_OPTIONS = ["支出", "收入"];

/* 收入来源 */
var INCOME_CATEGORY_OPTIONS = [
  "工资",      // 月薪、年终奖
  "兼职",      // 副业、零工
  "理财收益",   // 余额宝、基金、股票、利息
  "转账收款",   // 他人转账
  "红包",      // 微信红包、转账红包
  "报销",      // 公司报销、差旅报销
  "退款",      // 购物退款、押金退还
  "其他",      // 无法归入上述分类
];

/* 收入细类（按来源分组） */
var INCOME_SUBCATEGORY_OPTIONS = {
  "工资":     ["月薪", "年终奖", "绩效奖金"],
  "兼职":     ["副业", "零工"],
  "理财收益":  ["余额宝", "基金", "股票", "银行利息"],
  "转账收款":  ["他人转账"],
  "红包":     ["微信红包"],
  "报销":     ["差旅报销", "加班报销"],
  "退款":     ["购物退款", "押金退还"],
  "其他":     [],
};

/* ========== 分类图标（按大类 + 收入来源） ========== */
var CATS = {
  // 消费大类
  "餐饮":   { color: "#E8917A", icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 3v8a2 2 0 002 2h0a2 2 0 002-2V3 M7 13v8 M12 3v18 M12 3c2 0 3 2 3 5s-1 5-3 5" stroke-linecap="round" stroke-linejoin="round"/></svg>' },
  "交通":   { color: "#5B9BD5", icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="3" width="16" height="14" rx="2"/><path d="M4 11h16" stroke-linecap="round"/><circle cx="8" cy="20" r="1.5"/><circle cx="16" cy="20" r="1.5"/></svg>' },
  "住房":   { color: "#E85D5D", icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12l9-9 9 9M5 10v10h14V10" stroke-linecap="round" stroke-linejoin="round"/></svg>' },
  "购物":   { color: "#F5A623", icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 7h12l-1 14H7L6 7z M9 7V5a3 3 0 016 0v2" stroke-linecap="round" stroke-linejoin="round"/></svg>' },
  "居家":   { color: "#8B5E3C", icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" stroke-linecap="round" stroke-linejoin="round"/><path d="M9 22V12h6v10" stroke-linecap="round" stroke-linejoin="round"/></svg>' },
  "娱乐":   { color: "#FF6B9D", icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 5v14l7-4 7 4V5l-7 4z" stroke-linecap="round" stroke-linejoin="round"/></svg>' },
  "医疗":   { color: "#27AE60", icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M2 12h20" stroke-linecap="round"/><circle cx="12" cy="12" r="9"/></svg>' },
  "通讯":   { color: "#9B59B6", icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="2" width="12" height="20" rx="2"/><path d="M11 18h2" stroke-linecap="round"/></svg>' },
  "其他":   { color: "#7A7A7A", icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="6" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="18" cy="12" r="2"/></svg>' },
  // 收入来源
  "工资":   { color: "#5FB8A3", icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="5" width="20" height="14" rx="2"/><circle cx="12" cy="12" r="3"/></svg>' },
  "兼职":   { color: "#3D9B82", icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 7h-4a3 3 0 00-3-3H9a3 3 0 00-3 3v10a3 3 0 003 3h4a3 3 0 003-3v-4l4-3z" stroke-linecap="round" stroke-linejoin="round"/></svg>' },
  "理财收益": { color: "#5B9BD5", icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M5 9l7-7 7 7M5 15h14" stroke-linecap="round" stroke-linejoin="round"/></svg>' },
  "转账收款": { color: "#F5A623", icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7" stroke-linecap="round" stroke-linejoin="round"/></svg>' },
  "红包":   { color: "#FF6B9D", icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M4 9h16 M12 9v12 M12 9c-3 0-4-3-2-4s5 0 5 0 2-2 0-2" stroke-linecap="round" stroke-linejoin="round"/></svg>' },
  "报销":   { color: "#27AE60", icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 2h9l4 4v16H6z M15 2v4h4 M9 13h6 M9 17h6" stroke-linecap="round" stroke-linejoin="round"/></svg>' },
  "退款":   { color: "#E8917A", icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7v6h6M21 17v-6h-6" stroke-linecap="round" stroke-linejoin="round"/><path d="M6 13a8 8 0 101 4" stroke-linecap="round" stroke-linejoin="round"/></svg>' },
};

/* ========== 通用 SVG 图标 ========== */
var ICON = {
  download: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3v12M7 10l5 5 5-5M5 21h14" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  upload:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 15V3M7 8l5-5 5 5M5 21h14" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  trash:    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 7h16M9 7V5h6v2M6 7l1 14h10l1-14" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  alert:    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 20h20L12 2z M12 9v5 M12 18v.1" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  check:    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 13l4 4 10-10" stroke-linecap="round" stroke-linejoin="round"/></svg>'
};
