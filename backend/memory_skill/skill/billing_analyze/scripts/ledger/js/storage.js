"use strict";
/* ================================================================
 * 打工人小账本 · 数据存储
 * Storage Key、默认数据、数据读写、ID/日期/金额工具
 * 记录字段对齐 backend/.../billing/common.py 与 save_bill/save_income
 *
 * [数据库对接模式]
 * 本文件已从 localStorage 改为「内存缓存 + 后端桥接」：
 *   - 所有 getter/setter 名称保持不变，渲染层无需改动
 *   - initFromServer() 在启动时从 ledger_server.py 拉取 billing.db 数据
 *   - save() 写内存缓存后异步同步到后端（records 对账写入 SQLite）
 *   - 浏览器需通过 http 打开 ledger.html（见 ledger_server.py）
 * ================================================================ */

/* ========== Storage Key（仅作语义标识，实际存内存+后端） ========== */
var SK = {
  records: "wb_ledger_records",
  savings: "wb_ledger_savings",
  debts:   "wb_ledger_debts",
  meta:    "wb_ledger_meta"
};

var API_ROOT = "";           // 同源（由桥接服务器托管）
var DB = {                   // 内存缓存
  records: [],
  savings: [],
  debts: null,
  meta: null
};
var _loaded = false;         // 是否已从后端加载
var _syncTimer = null;       // 防抖同步计时器
var _syncing = false;        // 是否正在同步
var _dirtyRecords = false;   // 是否有待同步的 records 改动
var _dirtySettings = false;  // 是否有待同步的设置改动

/* ========== 默认配置 ========== */
/* 相对当前日期生成演示数据（新字段结构）。仅离线/无后端时兜底。 */
function defaultRecords(){
  function fmt(d){
    var y=d.getFullYear(), m=String(d.getMonth()+1).padStart(2,"0"), dd=String(d.getDate()).padStart(2,"0");
    return y+"-"+m+"-"+dd;
  }
  var now=new Date();
  function dayAgo(n){ var d=new Date(now); d.setDate(d.getDate()-n); return fmt(d); }
  return [
    { id: rid(), date: dayAgo(0), itemName: "午餐·外卖", category: "餐饮", subcategory: "外卖", direction: "支出", expenseType: "弹性支出", platform: "微信", amount: 32, note: "", demo: true },
    { id: rid(), date: dayAgo(0), itemName: "地铁通勤", category: "交通", subcategory: "公交地铁", direction: "支出", expenseType: "刚性必要", platform: "支付宝", amount: 12, note: "", demo: true },
    { id: rid(), date: dayAgo(1), itemName: "话费充值", category: "通讯", subcategory: "话费", direction: "支出", expenseType: "刚性固定", platform: "微信", amount: 200, note: "本月话费充值", demo: true },
    { id: rid(), date: dayAgo(1), itemName: "晚餐", category: "餐饮", subcategory: "堂食", direction: "支出", expenseType: "弹性支出", platform: "支付宝", amount: 35, note: "", demo: true },
    { id: rid(), date: dayAgo(2), itemName: "瑞幸 9.9", category: "餐饮", subcategory: "奶茶咖啡", direction: "支出", expenseType: "弹性支出", platform: "微信", amount: 28, note: "", demo: true },
    { id: rid(), date: dayAgo(3), itemName: "日用品", category: "购物", subcategory: "日用消耗", direction: "支出", expenseType: "弹性支出", platform: "现金", amount: 168, note: "", demo: true },
    { id: rid(), date: dayAgo(5), itemName: "同事聚餐AA", category: "餐饮", subcategory: "堂食", direction: "支出", expenseType: "弹性支出", platform: "支付宝", amount: 35, note: "", demo: true },
    { id: rid(), date: dayAgo(3), itemName: "8月工资", category: "工资", subcategory: "月薪", direction: "收入", expenseType: "", platform: "银行卡", amount: 12000, note: "", demo: true }
  ];
}

function defaultSavings(){
  var now=new Date();
  var m=now.getMonth();
  var months=[];
  for(var i=6;i>=1;i--){
    var d=new Date(now);
    d.setMonth(m-i+1);
    var label=(d.getMonth()+1)+"月";
    months.push(label);
  }
  var vals=[8000, 11500, 13500, 15000, 16500, 17800];
  return months.map(function(lbl,i){
    return { month: lbl, amount: vals[i] };
  });
}

function rid(){ return Date.now().toString(36)+Math.random().toString(36).slice(2,7); }

/* ========== 余额 / 欠款默认值 ========== */
function defaultDebts(){
  return {
    balances: [],   // {id, name, amount, platform, note}
    debts: []       // {id, name, amount, type, dueDate, note}
  };
}

/* ========== 数据读写（内存缓存） ========== */
function _keyName(key){
  return String(key).replace("wb_ledger_", "");
}

function load(key, fallback){
  var name = _keyName(key);
  var v = DB[name];
  return (v === undefined || v === null) ? fallback : v;
}

function save(key, val){
  var name = _keyName(key);
  DB[name] = val;
  // 触发异步同步到后端（防抖）
  if(name === "records"){
    _dirtyRecords = true;
  } else if(name === "savings" || name === "debts"){
    _dirtySettings = true;
  }
  _scheduleSync();
}

/* ========== 后端同步 ========== */
function _scheduleSync(){
  if(_syncTimer) clearTimeout(_syncTimer);
  _syncTimer = setTimeout(_flushSync, 400);
}

/* 立即触发一次同步（供保存记录后即时落库） */
function flushSync(){
  if(_syncTimer){ clearTimeout(_syncTimer); _syncTimer = null; }
  _flushSync();
}

function _flushSync(){
  if(_syncing) return;
  if(!_dirtyRecords && !_dirtySettings) return;

  _syncing = true;

  var doRecords = _dirtyRecords;
  var doSettings = _dirtySettings;
  _dirtyRecords = false;
  _dirtySettings = false;

  var pRecords = doRecords ? _post("/api/records", { records: DB.records }) : Promise.resolve(null);
  var pSettings = doSettings ? _post("/api/settings", {
    savings: DB.savings,
    debts: DB.debts
  }) : Promise.resolve(null);

  Promise.all([pRecords, pSettings]).then(function(res){
    _syncing = false;
    // 用后端返回的 records 回填 _dbId，保持对账一致
    if(res[0] && res[0].records && Array.isArray(res[0].records)){
      DB.records = res[0].records;
    }
    // 若同步期间又产生了新的改动，继续同步
    if(_dirtyRecords || _dirtySettings) _scheduleSync();
  }).catch(function(err){
    _syncing = false;
    console.warn("后端同步失败:", err);
    if(_dirtyRecords || _dirtySettings) _scheduleSync();
  });
}

function _post(url, payload){
  return fetch(API_ROOT + url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  }).then(function(res){
    if(!res.ok) throw new Error("HTTP " + res.status);
    return res.json();
  });
}

/* 直接调用 analyze_monthly.py 脚本，获取指定月份三层分析（不重写逻辑） */
function loadMonthAnalysis(year, month){
  return fetch(API_ROOT + "/api/analyze-monthly?year=" + year + "&month=" + month)
    .then(function(res){
      if(!res.ok) throw new Error("HTTP " + res.status);
      return res.json();
    })
    .then(function(data){
      return data.result || null;
    });
}

/* 直接调用 analyze_category_monthly.py 脚本，获取指定月份大类/细类汇总（不重写逻辑） */
function loadCategoryAnalysis(year, month){
  return fetch(API_ROOT + "/api/analyze-category-monthly?year=" + year + "&month=" + month)
    .then(function(res){
      if(!res.ok) throw new Error("HTTP " + res.status);
      return res.json();
    })
    .then(function(data){
      return data.result || null;
    });
}

/* ========== 从后端初始化加载 ========== */
function initFromServer(){
  return fetch(API_ROOT + "/api/state")
    .then(function(res){
      if(!res.ok) throw new Error("HTTP " + res.status);
      return res.json();
    })
    .then(function(state){
      DB.records  = Array.isArray(state.records) ? state.records : [];
      DB.savings  = Array.isArray(state.savings) ? state.savings : defaultSavings();
      DB.debts    = state.debts    || defaultDebts();
      DB.meta     = DB.meta || { firstOpen: false, demoLoaded: false };
      _loaded = true;
      return true;
    })
    .catch(function(err){
      console.warn("后端加载失败，回退到本地默认数据:", err);
      // 回退：本地 localStorage（历史数据）或演示数据
      DB.records = _readLocal(SK.records, []);
      DB.savings = defaultSavings();
      DB.debts = defaultDebts();
      _loaded = true;
      return false;
    });
}

function _readLocal(key, fallback){
  try{
    var raw = localStorage.getItem(key);
    if(raw === null) return fallback;
    return JSON.parse(raw);
  }catch(e){
    return fallback;
  }
}

/* ========== 便捷 getter/setter（保持旧接口不变） ========== */
function getRecords(){ return load(SK.records, []); }
function getSavings(){ var s=load(SK.savings,[]); return s.length?s:s; }

function getDebts(){
  var d = load(SK.debts, null);
  if(!d || typeof d !== "object"){ d = defaultDebts(); }
  if(!Array.isArray(d.balances)) d.balances = [];
  if(!Array.isArray(d.debts)) d.debts = [];
  return d;
}

function setRecords(v){ save(SK.records, v); }
function setSavings(v){ save(SK.savings, v); }
function setDebts(v){ save(SK.debts, v); }

function getMeta(){ return Object.assign({ firstOpen:true, demoLoaded:false }, load(SK.meta, {})); }
function setMeta(v){ save(SK.meta, v); }

/* ========== 记录工具（兼容字段语义） ========== */
function isExpense(r){ return r.direction === "支出"; }
function isIncome(r){ return r.direction === "收入"; }

/* ========== 日期/月份辅助 ========== */
function fmtMoney(n){
  n = Math.round(n*100)/100;
  return "¥" + n.toLocaleString("zh-CN", {minimumFractionDigits: n%1===0?0:2, maximumFractionDigits:2});
}
function currentYM(){
  var d = new Date();
  return { y:d.getFullYear(), m:d.getMonth()+1 };
}
function isThisMonth(dateStr){
  var ym = currentYM();
  var parts = String(dateStr).split("-");
  return parseInt(parts[0])===ym.y && parseInt(parts[1])===ym.m;
}
/* 判断 dateStr（YYYY-MM-DD）是否属于指定年月 */
function isInMonth(dateStr, y, m){
  var parts = String(dateStr).split("-");
  return parseInt(parts[0])===y && parseInt(parts[1])===m;
}
function todayStr(){
  var d = new Date();
  return d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0");
}
