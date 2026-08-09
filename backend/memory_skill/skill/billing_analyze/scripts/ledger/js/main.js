"use strict";
/* ================================================================
 * 打工人小账本 · 主入口
 * 全量渲染、初始化、事件绑定
 * ================================================================ */

/* ========== 全量渲染 ========== */
function renderAll(){
  renderHome();
  renderLedger();
  renderAssets();
  drawCalendar();
}

/* ========== 初始化 ========== */
function init(){
  // 数据库对接模式：先从桥接服务器加载数据，再渲染
  initFromServer().then(function(loaded){
    // 首次标记，避免再次触发演示数据写入
    var meta = getMeta();
    meta.firstOpen = false;
    setMeta(meta);

    if(!loaded && !meta.demoLoaded){
      // 后端不可用时回退演示数据（仅作离线兜底，不写回后端）
      if(!DB.records.length){
        DB.records = defaultRecords();
      }
    }

    bindEvents();
    renderToolbar();
    renderCalendar();
    renderAll();
  });
}

/* ========== 事件绑定 ========== */
function bindEvents(){
  document.querySelectorAll(".nav-item").forEach(function(el){
    el.addEventListener("click", function(){ switchPage(this.dataset.page); });
  });

  document.getElementById("importFile").addEventListener("change", function(e){
    if(e.target.files.length) importJSON(e.target.files[0]);
    e.target.value = "";
  });

  // 初始化「记一笔」表单
  if(typeof initAddForm === "function") initAddForm();
  // 初始化「资产负债」表单
  if(typeof initAssetsForm === "function") initAssetsForm();
}

if(document.readyState === "loading"){
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
