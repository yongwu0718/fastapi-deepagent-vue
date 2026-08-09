"use strict";
/* ================================================================
 * 打工人小账本 · 记账页渲染
 * 全部记录（支持筛选 + 排序）
 * ================================================================ */

/* ---------- 筛选 / 排序状态 ---------- */
var _ledgerFilter = {
  keyword: "",      // 关键词搜索（名称/备注/平台）
  dir: "",          // "" 全部 / "收入" / "支出"
  category: "",     // 大类
  expenseType: "",  // 消费类型
  platform: "",     // 支付平台
  dateFrom: "",     // 起始日期 YYYY-MM-DD
  dateTo: "",       // 结束日期 YYYY-MM-DD
  sortBy: "date",   // date / amount
  sortDir: "desc"   // asc / desc
};

function renderLedger(){
  renderAllRecords();
}

/* ========== 筛选 ========== */
function filterLedger(key, value){
  if(key === "reset"){
    _ledgerFilter = { keyword:"", dir:"", category:"", expenseType:"", platform:"", dateFrom:"", dateTo:"", sortBy:"date", sortDir:"desc" };
  } else {
    _ledgerFilter[key] = value;
  }
  renderAllRecords();
  syncLedgerControls();
}

function clearLedgerFilter(){
  filterLedger("reset");
}

function toggleSort(col){
  if(_ledgerFilter.sortBy === col){
    _ledgerFilter.sortDir = _ledgerFilter.sortDir === "desc" ? "asc" : "desc";
  } else {
    _ledgerFilter.sortBy = col;
    _ledgerFilter.sortDir = (col === "amount") ? "desc" : "desc";
  }
  renderAllRecords();
  syncLedgerControls();
}

/* 把状态同步回控件（外部触发 render 时刷新下拉选中态） */
function syncLedgerControls(){
  var el = document.getElementById("filterDir");
  if(el) el.value = _ledgerFilter.dir;
  el = document.getElementById("filterCategory");
  if(el) el.value = _ledgerFilter.category;
  el = document.getElementById("filterExpenseType");
  if(el) el.value = _ledgerFilter.expenseType;
  el = document.getElementById("filterPlatform");
  if(el) el.value = _ledgerFilter.platform;
  el = document.getElementById("filterDateFrom");
  if(el) el.value = _ledgerFilter.dateFrom;
  el = document.getElementById("filterDateTo");
  if(el) el.value = _ledgerFilter.dateTo;
}

function renderAllRecords(){
  var all = getRecords();
  var el = document.getElementById("allRecords");

  // 1) 关键词过滤
  var kw = (_ledgerFilter.keyword || "").trim().toLowerCase();
  var recs = all.filter(function(r){
    if(kw){
      var hay = [r.itemName, r.category, r.subcategory, r.platform, r.expenseType, r.note]
        .filter(Boolean).join(" ").toLowerCase();
      if(hay.indexOf(kw) < 0) return false;
    }
    if(_ledgerFilter.dir){
      if((isIncome(r) ? "收入" : "支出") !== _ledgerFilter.dir) return false;
    }
    if(_ledgerFilter.category && r.category !== _ledgerFilter.category) return false;
    if(_ledgerFilter.expenseType && r.expenseType !== _ledgerFilter.expenseType) return false;
    if(_ledgerFilter.platform && r.platform !== _ledgerFilter.platform) return false;
    var d = r.date || "";
    if(_ledgerFilter.dateFrom && d < _ledgerFilter.dateFrom) return false;
    if(_ledgerFilter.dateTo && d > _ledgerFilter.dateTo) return false;
    return true;
  });

  // 2) 排序
  var sortBy = _ledgerFilter.sortBy;
  var dir = _ledgerFilter.sortDir === "asc" ? 1 : -1;
  recs.sort(function(a, b){
    var va, vb;
    if(sortBy === "amount"){
      va = parseFloat(a.amount) || 0;
      vb = parseFloat(b.amount) || 0;
      return (va - vb) * dir;
    }
    // date（默认）：日期倒序，同日按 id 倒序
    va = a.date || "";
    vb = b.date || "";
    if(va === vb){
      return (parseFloat(a._dbId || a.id) || 0) < (parseFloat(b._dbId || b.id) || 0) ? dir : -dir;
    }
    return (va < vb ? -1 : 1) * dir;
  });

  var filteredCount = recs.length;
  document.getElementById("recordCount").textContent = filteredCount + " / " + all.length + " 条";

  // 3) 渲染工具栏 + 表
  var html = renderLedgerToolbar();

  if(recs.length === 0){
    el.innerHTML = html +
      '<div class="empty">'+ICON.check+'<div>'+
        (all.length === 0 ? '还没有记录，开始记第一笔吧' : '没有符合筛选条件的记录')+
      '</div></div>';
    return;
  }

  html += '<div class="ledger-table-wrap">'+
    '<table class="ledger-table">'+
      '<thead><tr>'+
        '<th class="sortable" onclick="toggleSort(\'date\')">日期'+sortCaret("date")+'</th>'+
        '<th>名称</th>'+
        '<th>收/支</th>'+
        '<th>大类</th>'+
        '<th>细类</th>'+
        '<th>消费类型</th>'+
        '<th class="sortable" onclick="toggleSort(\'amount\')">金额'+sortCaret("amount")+'</th>'+
        '<th>支付平台</th>'+
        '<th>备注</th>'+
        '<th></th>'+
      '</tr></thead><tbody>';

  recs.forEach(function(r){
    var isInc = isIncome(r);
    var cls = isInc ? "income" : "expense";
    var sign = isInc ? "+" : "−";
    var sub = r.subcategory ? r.category+" · "+r.subcategory : r.category;
    html += '<tr class="lt-row '+cls+'">'+
      '<td class="lt-date">'+escapeHtml(r.date||'')+'</td>'+
      '<td class="lt-name">'+(r.demo?'<span style="color:var(--gold);font-size:10px;">[示例]</span> ':'')+escapeHtml(r.itemName||sub)+'</td>'+
      '<td class="lt-dir"><span class="lt-badge '+cls+'">'+(isInc?'收入':'支出')+'</span></td>'+
      '<td>'+escapeHtml(r.category||'')+'</td>'+
      '<td>'+escapeHtml(r.subcategory||'')+'</td>'+
      '<td>'+(isInc ? '—' : escapeHtml(r.expenseType||''))+'</td>'+
      '<td class="lt-amt '+cls+'">'+sign+fmtMoney(r.amount||0)+'</td>'+
      '<td>'+escapeHtml(r.platform||'')+'</td>'+
      '<td class="lt-note">'+escapeHtml(r.note||'')+'</td>'+
      '<td><button class="record-del" onclick="deleteRecord(\''+r.id+'\')">'+ICON.trash+'</button></td>'+
    '</tr>';
  });

  html += '</tbody></table></div>';
  el.innerHTML = html;
}

function sortCaret(col){
  if(_ledgerFilter.sortBy !== col) return "";
  return _ledgerFilter.sortDir === "desc" ? " ▾" : " ▴";
}

/* ========== 筛选工具栏 ========== */
function renderLedgerToolbar(){
  var recs = getRecords();
  var cats = {}, exps = {}, plats = {};
  recs.forEach(function(r){
    if(r.category) cats[r.category] = true;
    if(!isIncome(r) && r.expenseType) exps[r.expenseType] = true;
    if(r.platform) plats[r.platform] = true;
  });

  function opts(map, sel){
    var h = '<option value="">全部</option>';
    Object.keys(map).sort().forEach(function(k){
      h += '<option value="'+escapeAttr(k)+'"'+(k===sel?' selected':'')+'>'+escapeHtml(k)+'</option>';
    });
    return h;
  }

  var hasFilter = _ledgerFilter.keyword || _ledgerFilter.dir || _ledgerFilter.category ||
                  _ledgerFilter.expenseType || _ledgerFilter.platform ||
                  _ledgerFilter.dateFrom || _ledgerFilter.dateTo;

  return '<div class="ledger-toolbar">'+
    '<div class="lt-search">'+
      '<input class="input" type="text" id="filterKeyword" placeholder="搜索名称/备注/平台…" value="'+escapeAttr(_ledgerFilter.keyword)+'" oninput="onKeywordInput(this.value)">'+
      (hasFilter ? '<button class="btn btn-sm btn-outline" onclick="clearLedgerFilter()" style="flex-shrink:0">✕ 清空</button>' : '')+
    '</div>'+
    '<div class="lt-filters">'+
      '<select class="input" id="filterDir" onchange="filterLedger(\'dir\',this.value)">'+
        '<option value="">收/支：全部</option>'+
        '<option value="收入"'+(_ledgerFilter.dir==="收入"?' selected':'')+'>收入</option>'+
        '<option value="支出"'+(_ledgerFilter.dir==="支出"?' selected':'')+'>支出</option>'+
      '</select>'+
      '<select class="input" id="filterCategory" onchange="filterLedger(\'category\',this.value)">'+opts(cats, _ledgerFilter.category)+'</select>'+
      '<select class="input" id="filterExpenseType" onchange="filterLedger(\'expenseType\',this.value)">'+opts(exps, _ledgerFilter.expenseType)+'</select>'+
      '<select class="input" id="filterPlatform" onchange="filterLedger(\'platform\',this.value)">'+opts(plats, _ledgerFilter.platform)+'</select>'+
    '</div>'+
    '<div class="lt-dates">'+
      '<span class="lt-date-label">日期</span>'+
      '<input class="input" type="date" id="filterDateFrom" value="'+escapeAttr(_ledgerFilter.dateFrom)+'" onchange="filterLedger(\'dateFrom\',this.value)">'+
      '<span class="lt-date-sep">至</span>'+
      '<input class="input" type="date" id="filterDateTo" value="'+escapeAttr(_ledgerFilter.dateTo)+'" onchange="filterLedger(\'dateTo\',this.value)">'+
    '</div>'+
  '</div>';
}

function onKeywordInput(v){
  _ledgerFilter.keyword = v;
  renderAllRecords();
}
