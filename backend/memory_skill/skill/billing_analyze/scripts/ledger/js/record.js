"use strict";
/* ================================================================
 * 打工人小账本 · 记录操作
 * 删除记录 / 新增记录（记一笔表单）
 * 字段对齐 save_bill / save_income（common.py 约束）
 * ================================================================ */

/* ========== 当前选择的收支方向（支出/收入） ========== */
var _addDir = "支出";

/* ========== 初始化「记一笔」表单 ========== */
function initAddForm(){
  var dirBtns = document.querySelectorAll("#dirToggle .dir-btn");
  dirBtns.forEach(function(btn){
    btn.addEventListener("click", function(){
      _addDir = btn.dataset.dir;
      dirBtns.forEach(function(b){ b.classList.toggle("active", b === btn); });
      refreshCategoryOptions();
      refreshSubcategoryOptions();
      toggleExpenseTypeRow();
    });
  });

  var catSel = document.getElementById("addCategory");
  catSel.addEventListener("change", refreshSubcategoryOptions);

  // 填充消费类型 / 支付平台（固定选项）
  fillSelect("addExpenseType", [""].concat(EXPENSE_TYPE_OPTIONS));
  fillSelect("addPlatform", [""].concat(PLATFORM_OPTIONS));

  // 默认日期 = 今天
  document.getElementById("addDate").value = todayStr();

  // 初始下拉
  refreshCategoryOptions();
  refreshSubcategoryOptions();
  toggleExpenseTypeRow();

  // 提交
  document.getElementById("addRecordBtn").addEventListener("click", addRecord);
}

/* 根据当前方向填充大类选项 */
function refreshCategoryOptions(){
  var cats = (_addDir === "收入") ? INCOME_CATEGORY_OPTIONS : CATEGORY_OPTIONS;
  fillSelect("addCategory", [""].concat(cats));
  refreshSubcategoryOptions();
}

/* 根据当前大类填充细类选项 */
function refreshSubcategoryOptions(){
  var cat = document.getElementById("addCategory").value;
  var subMap = (_addDir === "收入") ? INCOME_SUBCATEGORY_OPTIONS : SUBCATEGORY_OPTIONS;
  var subs = subMap[cat] || [];
  fillSelect("addSubcategory", [""].concat(subs));
}

/* 收入时隐藏「消费类型」列 */
function toggleExpenseTypeRow(){
  var row = document.getElementById("expenseTypeRow");
  if(_addDir === "收入"){
    row.classList.add("hidden");
  } else {
    row.classList.remove("hidden");
  }
}

/* 通用：填充 select */
function fillSelect(id, options){
  var sel = document.getElementById(id);
  if(!sel) return;
  sel.innerHTML = options.map(function(o){
    return '<option value="' + escapeAttr(o) + '">' + escapeHtml(o === "" ? "（不选）" : o) + '</option>';
  }).join("");
}

function escapeHtml(s){
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}
function escapeAttr(s){
  return String(s).replace(/&/g,"&amp;").replace(/"/g,"&quot;");
}

/* ========== 新增一条记录 ========== */
function addRecord(){
  var amount = parseFloat(document.getElementById("addAmount").value);
  var date = document.getElementById("addDate").value;
  var name = document.getElementById("addName").value.trim();
  var category = document.getElementById("addCategory").value;
  var subcategory = document.getElementById("addSubcategory").value;
  var expenseType = document.getElementById("addExpenseType").value;
  var platform = document.getElementById("addPlatform").value;
  var note = document.getElementById("addNote").value.trim();

  if(!amount || amount <= 0){
    toast("请输入有效金额");
    return;
  }
  if(!date){
    toast("请选择日期");
    return;
  }
  if(!category){
    toast("请选择大类");
    return;
  }

  var rec = {
    id: rid(),
    date: date,
    itemName: name || (subcategory || category),
    category: category,
    subcategory: subcategory || "",
    direction: _addDir,
    expenseType: (_addDir === "支出") ? (expenseType || "未分类") : "",
    platform: platform || "",
    amount: amount,
    note: note || ""
  };

  var recs = getRecords();
  recs.unshift(rec);
  setRecords(recs);
  flushSync();   // 立即落库 -> POST /api/records -> save_records() INSERT
  toast("已记录 " + fmtMoney(amount));

  // 清空表单（保留日期和方向）
  document.getElementById("addAmount").value = "";
  document.getElementById("addName").value = "";
  document.getElementById("addNote").value = "";
  document.getElementById("addCategory").value = "";
  refreshSubcategoryOptions();
  if(_addDir === "支出"){
    document.getElementById("addExpenseType").value = "";
  }
  document.getElementById("addPlatform").value = "";

  renderAll();
}

/* ========== 删除记录 ========== */
function deleteRecord(id){
  var recs = getRecords().filter(function(r){ return String(r.id) !== String(id); });
  setRecords(recs);
  flushSync();  // 立即落库（后端按全量对账删除对应行）
  toast("已删除");
  renderAll();
}
