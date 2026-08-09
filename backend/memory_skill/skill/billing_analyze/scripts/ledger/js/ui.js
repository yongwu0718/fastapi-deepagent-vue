"use strict";
/* ================================================================
 * 打工人小账本 · UI 基础
 * 页面切换、Toast、Modal、导出导入、按钮工具栏、进度环
 * ================================================================ */

/* ========== 页面切换 ========== */
var currentPage = "home";
function switchPage(name){
  currentPage = name;
  var pages = document.querySelectorAll(".page");
  for(var i=0;i<pages.length;i++) pages[i].classList.remove("active");
  var el = document.getElementById("page-"+name);
  if(el) el.classList.add("active");

  var navs = document.querySelectorAll(".nav-item");
  for(var j=0;j<navs.length;j++) navs[j].classList.toggle("active", navs[j].dataset.page===name);

  closeSidebar();
  window.scrollTo(0,0);
}

/* ========== 抽屉式侧栏 ========== */
function openSidebar(){
  var sb = document.getElementById("sidebar");
  var ov = document.getElementById("drawerOverlay");
  if(sb) sb.classList.add("open");
  if(ov) ov.classList.add("show");
}
function closeSidebar(){
  var sb = document.getElementById("sidebar");
  var ov = document.getElementById("drawerOverlay");
  if(sb) sb.classList.remove("open");
  if(ov) ov.classList.remove("show");
}
function toggleSidebar(){
  var sb = document.getElementById("sidebar");
  if(sb && sb.classList.contains("open")) closeSidebar();
  else openSidebar();
}

/* ========== Toast ========== */
function toast(msg){
  var c = document.getElementById("toastContainer");
  var t = document.createElement("div");
  t.className = "toast";
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(function(){ t.remove(); }, 3000);
}

/* ========== Modal ========== */
var modalCallback = null;
function showModal(title, text, iconHTML, onConfirm){
  document.getElementById("modalTitle").textContent = title;
  document.getElementById("modalText").textContent = text;
  document.getElementById("modalIcon").innerHTML = iconHTML || ICON.alert;
  document.getElementById("modalOverlay").classList.add("show");
  modalCallback = onConfirm;
}
function closeModal(){
  document.getElementById("modalOverlay").classList.remove("show");
  modalCallback = null;
}
document.getElementById("modalConfirmBtn").addEventListener("click", function(){
  var cb = modalCallback;
  closeModal();
  if(cb) cb();
});

/* ========== 导出导入 ========== */
function exportJSON(){
  var data = {
    exportedAt: new Date().toISOString(),
    records: load(SK.records, []),
    savings: load(SK.savings, []),
    debts: load(SK.debts, defaultDebts())
  };
  var json = JSON.stringify(data, null, 2);
  var blob = new Blob([json], {type:"application/json"});
  var url = URL.createObjectURL(blob);
  var a = document.createElement("a");
  a.href = url;
  var d = new Date();
  a.download = "打工人小账本_"+d.getFullYear()+String(d.getMonth()+1).padStart(2,"0")+String(d.getDate()).padStart(2,"0")+".json";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  toast("已导出 JSON 备份");
}

function importJSON(file){
  var reader = new FileReader();
  reader.onload = function(e){
    try{
      var data = JSON.parse(e.target.result);
      if(data.records && Array.isArray(data.records)) save(SK.records, data.records);
      if(data.savings && Array.isArray(data.savings)) save(SK.savings, data.savings);
      if(data.debts) save(SK.debts, data.debts);
      flushSync();
      toast("导入成功，数据已恢复");
      renderAll();
    }catch(err){
      toast("导入失败：文件格式不对");
    }
  };
  reader.readAsText(file);
}

function clearDemoData(){
  showModal(
    "清空示例数据",
    "将删除所有标记为「示例」的记录，恢复到空白状态。你的自定义数据不受影响。",
    ICON.trash,
    function(){
      var recs = getRecords().filter(function(r){ return !r.demo; });
      setRecords(recs);
      flushSync();
      toast("示例数据已清空");
      renderAll();
    }
  );
}

function clearAllData(){
  showModal(
    "清空全部数据",
    "⚠️ 此操作不可撤销！所有记账记录、基金设置都将被删除。",
    ICON.trash,
    function(){
      // 清空内存缓存
      DB.records = [];
      DB.savings = [];
      DB.debts = defaultDebts();
      // 同步到后端（删除所有 DB 记录 + 重置设置）
      _dirtyRecords = true;
      _dirtySettings = true;
      flushSync();
      toast("全部数据已清空");
      renderAll();
    }
  );
}

/* ========== 按钮工具栏渲染 ========== */
function renderToolbar(){
  var btns =
    '<button class="btn btn-sm btn-outline" onclick="exportJSON()">'+ICON.download+'导出</button>'+
    '<button class="btn btn-sm btn-outline" onclick="document.getElementById(\'importFile\').click()">'+ICON.upload+'导入</button>'+
    '<button class="btn btn-sm btn-outline" onclick="clearDemoData()">'+ICON.trash+'清示例</button>';
  document.getElementById("sidebarFoot").innerHTML = btns;
}
