"use strict";
/* ================================================================
 * 打工人小账本 · 资产负债页渲染
 * 余额管理 + 欠款管理（JSON 存储，走 /api/settings 同步）
 * ================================================================ */

function renderAssets(){
  renderAssetsOverview();
  renderBalanceList();
  renderDebtList();
}

/* ========== 净资产概览 ========== */
function renderAssetsOverview(){
  var data = getDebts();
  var totalBalance = (data.balances || []).reduce(function(s, b){ return s + (parseFloat(b.amount) || 0); }, 0);
  var totalDebt    = (data.debts || []).reduce(function(s, d){
    var rem = parseFloat(d.remaining);
    return s + (isNaN(rem) ? (parseFloat(d.amount) || 0) : rem);
  }, 0);
  var totalDebtOriginal = (data.debts || []).reduce(function(s, d){ return s + (parseFloat(d.amount) || 0); }, 0);
  var netAssets    = totalBalance - totalDebt;

  document.getElementById("assetsOverview").innerHTML =
    '<div class="stat-card">'+
      '<div class="stat-label">总余额</div>'+
      '<div class="stat-val income">'+fmtMoney(totalBalance)+'</div>'+
      '<div class="stat-sub">'+(data.balances||[]).length+' 个账户</div>'+
    '</div>'+
    '<div class="stat-card">'+
      '<div class="stat-label">剩余应还</div>'+
      '<div class="stat-val expense">'+fmtMoney(totalDebt)+'</div>'+
      '<div class="stat-sub">'+(data.debts||[]).length+' 笔欠款</div>'+
    '</div>'+
    '<div class="stat-card">'+
      '<div class="stat-label">已还金额</div>'+
      '<div class="stat-val income">'+fmtMoney(totalDebtOriginal - totalDebt)+'</div>'+
      '<div class="stat-sub">总计 '+fmtMoney(totalDebtOriginal)+'</div>'+
    '</div>'+
    '<div class="stat-card">'+
      '<div class="stat-label">净资产</div>'+
      '<div class="stat-val '+(netAssets>=0?'income':'expense')+'">'+(netAssets>=0?'+':'')+fmtMoney(netAssets)+'</div>'+
      '<div class="stat-sub">'+(netAssets>=0?'资产>负债':'资不抵债')+'</div>'+
    '</div>';
}

/* ========== 余额列表 ========== */
function renderBalanceList(){
  var data = getDebts();
  var list = data.balances || [];
  var el = document.getElementById("balanceList");
  document.getElementById("balanceCount").textContent = list.length + " 项";

  if(list.length === 0){
    el.innerHTML = '<div class="empty">'+ICON.check+'<div>还没有余额记录</div></div>';
    return;
  }

  el.innerHTML = list.map(function(b){
    var cfg = CATS[b.platform] || {color:"#5FB8A3", icon: ICON.check};
    return '<div class="record-item">'+
      '<div class="record-icon" style="background:'+cfg.color+'15;color:'+cfg.color+'">'+
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><path d="M3 10h18M5 10v8h14v-8" stroke-linecap="round" stroke-linejoin="round"/></svg>'+
      '</div>'+
      '<div class="record-info" onclick="editBalance(\''+b.id+'\')" style="cursor:pointer">'+
        '<div class="record-cat">'+escapeHtml(b.name||'')+'</div>'+
        '<div class="record-note">'+escapeHtml(b.platform||'')+(b.note?' · '+escapeHtml(b.note):'')+'</div>'+
      '</div>'+
      '<div style="text-align:right">'+
        '<div class="record-amt income">'+fmtMoney(b.amount||0)+'</div>'+
        '<button class="btn btn-sm btn-outline" style="margin-top:4px;min-height:28px;font-size:11px;padding:4px 10px" onclick="editBalance(\''+b.id+'\')">编辑</button>'+
      '</div>'+
      '<button class="record-del" onclick="deleteBalance(\''+b.id+'\')">'+ICON.trash+'</button>'+
    '</div>';
  }).join("");
}

/* ========== 欠款列表 ========== */
function renderDebtList(){
  var data = getDebts();
  var list = data.debts || [];
  var el = document.getElementById("debtList");
  document.getElementById("debtCount").textContent = list.length + " 项";

  if(list.length === 0){
    el.innerHTML = '<div class="empty">'+ICON.check+'<div>没有欠款，保持下去！</div></div>';
    return;
  }

  el.innerHTML = list.map(function(d){
    var typeColor = {"信用卡":"#E8917A","花呗":"#5B9BD5","借款":"#F5A623","房贷":"#E85D5D","车贷":"#9B59B6","其他":"#7A7A7A"}[d.type] || "#7A7A7A";
    var dueStr = d.dueDate ? ' · 到期 '+d.dueDate.slice(5) : '';
    var overdue = d.dueDate && d.dueDate < todayStr();
    var remaining = parseFloat(d.remaining);
    if(isNaN(remaining)) remaining = parseFloat(d.amount) || 0;
    var paidOff = remaining <= 0;
    var progress = d.amount > 0 ? Math.round((1 - remaining / d.amount) * 100) : 0;
    return '<div class="record-item debt-item">'+
      '<div class="record-icon" style="background:'+typeColor+'15;color:'+typeColor+'">'+
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><path d="M12 8v4M12 16v.01M22 12a10 10 0 11-20 0 10 10 0 0120 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>'+
      '</div>'+
      '<div class="record-info" onclick="editDebt(\''+d.id+'\')" style="cursor:pointer">'+
        '<div class="record-cat">'+escapeHtml(d.name||'')+' <span style="font-size:10px;color:'+typeColor+';background:'+typeColor+'15;padding:1px 6px;border-radius:8px;margin-left:4px">'+escapeHtml(d.type||'')+'</span>'+
          (overdue ? '<span style="font-size:10px;color:#fff;background:#E85D5D;padding:1px 6px;border-radius:8px;margin-left:4px">逾期</span>' : '')+
          (paidOff ? '<span style="font-size:10px;color:#fff;background:var(--mint);padding:1px 6px;border-radius:8px;margin-left:4px">已还清</span>' : '')+
        '</div>'+
        '<div class="record-note">总额 '+fmtMoney(d.amount||0)+' · 剩余 '+fmtMoney(remaining)+(d.note?' · '+escapeHtml(d.note):'')+dueStr+'</div>'+
        '<div class="debt-progress">'+
          '<div class="debt-progress-bar" style="width:'+progress+'%;background:'+(paidOff?'var(--mint)':typeColor)+'"></div>'+
        '</div>'+
      '</div>'+
      '<div style="text-align:right;flex-shrink:0">'+
        '<div class="record-amt expense">'+fmtMoney(remaining)+'</div>'+
        '<div style="display:flex;gap:4px;justify-content:flex-end;margin-top:4px">'+
          '<button class="btn btn-sm btn-outline" style="min-height:28px;font-size:11px;padding:4px 8px" onclick="repayDebt(\''+d.id+'\')">还款</button>'+
          '<button class="btn btn-sm btn-outline" style="min-height:28px;font-size:11px;padding:4px 8px" onclick="editDebt(\''+d.id+'\')">编辑</button>'+
        '</div>'+
      '</div>'+
      '<button class="record-del" onclick="deleteDebt(\''+d.id+'\')">'+ICON.trash+'</button>'+
    '</div>';
  }).join("");
}

/* ========== 新增余额 ========== */
function addBalance(){
  var name = document.getElementById("balName").value.trim();
  var amount = parseFloat(document.getElementById("balAmount").value);
  var platform = document.getElementById("balPlatform").value;
  var note = document.getElementById("balNote").value.trim();

  if(!name){ toast("请填写名称"); return; }
  if(!amount || amount <= 0){ toast("请输入有效金额"); return; }

  var data = getDebts();
  data.balances.push({
    id: rid(),
    name: name,
    amount: amount,
    platform: platform || "",
    note: note || ""
  });
  setDebts(data);
  flushSync();
  toast("余额已添加");

  // 清空表单
  document.getElementById("balName").value = "";
  document.getElementById("balAmount").value = "";
  document.getElementById("balNote").value = "";
  document.getElementById("balPlatform").value = "";
  renderAssets();
}

/* ========== 新增欠款 ========== */
function addDebt(){
  var name = document.getElementById("debtName").value.trim();
  var amount = parseFloat(document.getElementById("debtAmount").value);
  var remaining = parseFloat(document.getElementById("debtRemaining").value);
  var type = document.getElementById("debtType").value;
  var dueDate = document.getElementById("debtDueDate").value;
  var note = document.getElementById("debtNote").value.trim();

  if(!name){ toast("请填写名称"); return; }
  if(!amount || amount <= 0){ toast("请输入有效总金额"); return; }

  // 剩余应还默认等于总金额
  if(isNaN(remaining) || remaining < 0){ remaining = amount; }

  var data = getDebts();
  data.debts.push({
    id: rid(),
    name: name,
    amount: amount,
    remaining: remaining,
    type: type || "其他",
    dueDate: dueDate || "",
    note: note || ""
  });
  setDebts(data);
  flushSync();
  toast("欠款已添加");

  // 清空表单
  document.getElementById("debtName").value = "";
  document.getElementById("debtAmount").value = "";
  document.getElementById("debtRemaining").value = "";
  document.getElementById("debtDueDate").value = "";
  document.getElementById("debtNote").value = "";
  renderAssets();
}

/* ========== 删除 ========== */
function deleteBalance(id){
  var data = getDebts();
  data.balances = data.balances.filter(function(b){ return String(b.id) !== String(id); });
  setDebts(data);
  flushSync();
  toast("已删除");
  renderAssets();
}

function deleteDebt(id){
  var data = getDebts();
  data.debts = data.debts.filter(function(d){ return String(d.id) !== String(id); });
  setDebts(data);
  flushSync();
  toast("已删除");
  renderAssets();
}

/* ========== 还款（减少剩余应还） ========== */
function repayDebt(id){
  var data = getDebts();
  var d = data.debts.find(function(x){ return String(x.id) === String(id); });
  if(!d) return;

  var curRem = parseFloat(d.remaining);
  if(isNaN(curRem)) curRem = parseFloat(d.amount) || 0;

  var input = prompt("输入还款金额（当前剩余 "+fmtMoney(curRem)+"）：", "");
  if(input === null) return;
  var pay = parseFloat(input);
  if(isNaN(pay) || pay <= 0){ toast("请输入有效金额"); return; }

  var newRem = Math.max(0, curRem - pay);
  d.remaining = newRem;
  setDebts(data);
  flushSync();
  toast("已还款 "+fmtMoney(pay)+"，剩余 "+fmtMoney(newRem));
  renderAssets();
}

/* ========== 初始化表单 ========== */
function initAssetsForm(){
  // 填充余额平台下拉（复用 PLATFORM_OPTIONS）
  var balSel = document.getElementById("balPlatform");
  if(balSel){
    balSel.innerHTML = '<option value="">（不选）</option>' +
      PLATFORM_OPTIONS.map(function(p){ return '<option value="'+escapeAttr(p)+'">'+escapeHtml(p)+'</option>'; }).join("");
  }

  // 绑定按钮
  var addBalBtn = document.getElementById("addBalanceBtn");
  if(addBalBtn) addBalBtn.addEventListener("click", addBalance);

  var addDebtBtn = document.getElementById("addDebtBtn");
  if(addDebtBtn) addDebtBtn.addEventListener("click", addDebt);
}

/* ========== 编辑弹层 ========== */
var _editType = null;   // "balance" | "debt"
var _editId   = null;

function editBalance(id){
  var data = getDebts();
  var b = (data.balances || []).find(function(x){ return String(x.id) === String(id); });
  if(!b) return;
  _editType = "balance";
  _editId = id;

  var body =
    '<div class="form-row"><div class="form-col">'+
      '<label class="label">名称</label>'+
      '<input class="input" type="text" id="editName" value="'+escapeAttr(b.name||'')+'" maxlength="20">'+
    '</div></div>'+
    '<div class="form-row">'+
      '<div class="form-col"><label class="label">金额</label>'+
        '<input class="input" type="number" id="editAmount" value="'+(b.amount||0)+'" min="0" step="0.01" inputmode="decimal"></div>'+
      '<div class="form-col"><label class="label">平台</label>'+
        '<select class="input" id="editPlatform"><option value="">（不选）</option>'+
          PLATFORM_OPTIONS.map(function(p){ return '<option value="'+escapeAttr(p)+'"'+(p===b.platform?' selected':'')+'>'+escapeHtml(p)+'</option>'; }).join("")+
        '</select></div>'+
    '</div>'+
    '<div class="form-row"><div class="form-col">'+
      '<label class="label">备注</label>'+
      '<input class="input" type="text" id="editNote" value="'+escapeAttr(b.note||'')+'" maxlength="40">'+
    '</div></div>';

  showEditModal("编辑余额", body, "saveEditBalance()");
}

function editDebt(id){
  var data = getDebts();
  var d = (data.debts || []).find(function(x){ return String(x.id) === String(id); });
  if(!d) return;
  _editType = "debt";
  _editId = id;

  var remaining = parseFloat(d.remaining);
  if(isNaN(remaining)) remaining = parseFloat(d.amount) || 0;

  var typeOpts = ["信用卡","花呗","借款","房贷","车贷","其他"];
  var body =
    '<div class="form-row"><div class="form-col">'+
      '<label class="label">名称</label>'+
      '<input class="input" type="text" id="editName" value="'+escapeAttr(d.name||'')+'" maxlength="20">'+
    '</div></div>'+
    '<div class="form-row">'+
      '<div class="form-col"><label class="label">总金额</label>'+
        '<input class="input" type="number" id="editAmount" value="'+(d.amount||0)+'" min="0" step="0.01" inputmode="decimal"></div>'+
      '<div class="form-col"><label class="label">剩余应还</label>'+
        '<input class="input" type="number" id="editRemaining" value="'+remaining+'" min="0" step="0.01" inputmode="decimal"></div>'+
    '</div>'+
    '<div class="form-row">'+
      '<div class="form-col"><label class="label">类型</label>'+
        '<select class="input" id="editType">'+
          typeOpts.map(function(t){ return '<option value="'+t+'"'+(t===d.type?' selected':'')+'>'+t+'</option>'; }).join("")+
        '</select></div>'+
      '<div class="form-col"><label class="label">到期日</label>'+
        '<input class="input" type="date" id="editDueDate" value="'+escapeAttr(d.dueDate||'')+'"></div>'+
    '</div>'+
    '<div class="form-row"><div class="form-col">'+
      '<label class="label">备注</label>'+
      '<input class="input" type="text" id="editNote" value="'+escapeAttr(d.note||'')+'" maxlength="40">'+
    '</div></div>';

  showEditModal("编辑欠款", body, "saveEditDebt()");
}

function showEditModal(title, bodyHTML, onSaveCall){
  var overlay = document.getElementById("editModalOverlay");
  if(!overlay) return;
  document.getElementById("editModalTitle").textContent = title;
  document.getElementById("editModalBody").innerHTML = bodyHTML;
  document.getElementById("editModalSaveBtn").setAttribute("onclick", onSaveCall);
  overlay.classList.add("show");
}

function closeEditModal(){
  var overlay = document.getElementById("editModalOverlay");
  if(overlay) overlay.classList.remove("show");
  _editType = null;
  _editId = null;
}

// 点击背景关闭
document.addEventListener("DOMContentLoaded", function(){
  var ov = document.getElementById("editModalOverlay");
  if(ov){
    ov.addEventListener("click", function(e){
      if(e.target === ov) closeEditModal();
    });
  }
});

function saveEditBalance(){
  if(_editType !== "balance" || !_editId) return;
  var name = document.getElementById("editName").value.trim();
  var amount = parseFloat(document.getElementById("editAmount").value);
  var platform = document.getElementById("editPlatform").value;
  var note = document.getElementById("editNote").value.trim();

  if(!name){ toast("请填写名称"); return; }
  if(!amount || amount <= 0){ toast("请输入有效金额"); return; }

  var data = getDebts();
  var b = (data.balances || []).find(function(x){ return String(x.id) === String(_editId); });
  if(!b){ toast("记录不存在"); closeEditModal(); return; }

  b.name = name;
  b.amount = amount;
  b.platform = platform || "";
  b.note = note || "";
  setDebts(data);
  flushSync();
  toast("已保存");
  closeEditModal();
  renderAssets();
}

function saveEditDebt(){
  if(_editType !== "debt" || !_editId) return;
  var name = document.getElementById("editName").value.trim();
  var amount = parseFloat(document.getElementById("editAmount").value);
  var remaining = parseFloat(document.getElementById("editRemaining").value);
  var type = document.getElementById("editType").value;
  var dueDate = document.getElementById("editDueDate").value;
  var note = document.getElementById("editNote").value.trim();

  if(!name){ toast("请填写名称"); return; }
  if(!amount || amount <= 0){ toast("请输入有效总金额"); return; }
  if(isNaN(remaining) || remaining < 0) remaining = amount;

  var data = getDebts();
  var d = (data.debts || []).find(function(x){ return String(x.id) === String(_editId); });
  if(!d){ toast("记录不存在"); closeEditModal(); return; }

  d.name = name;
  d.amount = amount;
  d.remaining = remaining;
  d.type = type || "其他";
  d.dueDate = dueDate || "";
  d.note = note || "";
  setDebts(data);
  flushSync();
  toast("已保存");
  closeEditModal();
  renderAssets();
}
