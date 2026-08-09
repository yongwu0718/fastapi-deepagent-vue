"use strict";
/* ================================================================
 * 打工人小账本 · 首页渲染
 * 月度概览、最近记录、自由基金环
 * 记录字段：direction(支出/收入)、category、subcategory、itemName
 * ================================================================ */

function renderHome(){
  renderMonthStats();
  renderRecentRecords();
}

function renderMonthStats(y, m){
  // 与日历当前查看月份关联（默认取日历当前月份）
  if(typeof y === "undefined"){ y = calYear; m = calMonth; }
  var el = document.getElementById("monthStats");
  el.innerHTML = "";

  // 直接使用 analyze_monthly.py 脚本运行结果渲染（口径与脚本完全一致）
  loadMonthAnalysis(y, m).then(function(res){
    if(!res || !res.monthly_income_expense){ renderMonthStatsLocal(y, m); return; }
    var rows = res.monthly_income_expense || [];
    var ym = y + "-" + pad2m(m);
    var row = null;
    for(var i=0;i<rows.length;i++){
      if(rows[i].month === ym){ row = rows[i]; break; }
    }
    if(!row){ renderMonthStatsLocal(y, m); return; }

    var monthLabel = y + "年" + m + "月";
    var isCur = (y === currentYM().y && m === currentYM().m);

    el.innerHTML = [
      { label:(isCur?"本月收入":monthLabel+"收入"), val: fmtMoney(row.total_income), cls:"income", sub:"真实收入 "+fmtMoney(row.real_income) },
      { label:"总支出", val: fmtMoney(row.expense), cls:"expense", sub:"固定 "+fmtMoney(row.rigid_fixed)+" / 必要 "+fmtMoney(row.rigid_necessary)+" / 弹性 "+fmtMoney(row.flexible) },
      { label:"弹性支出", val: fmtMoney(row.flexible), cls:"expense", sub:"负担率 "+rate(row.flexible_burden_rate) },
      { label:"本月结余", val: fmtMoney(row.net), cls: row.net>=0?"income":"expense", sub:(row.evaluation||"") }
    ].map(function(s){
      return '<div class="stat-card">'+
        '<div class="stat-label">'+s.label+'</div>'+
        '<div class="stat-val '+s.cls+'">'+s.val+'</div>'+
        '<div class="stat-sub">'+(s.sub||"")+'</div>'+
      '</div>';
    }).join("");
  }).catch(function(){ renderMonthStatsLocal(y, m); });

  // 独立渲染消费大类/细类（不依赖 analyze_monthly 是否成功）
  renderCategoryAnalysis(y, m);
}

/* 渲染消费大类/细类明细（analyze_category_monthly.py 脚本结果） */
function renderCategoryAnalysis(y, m){
  var el = document.getElementById("categoryAnalysis");
  if(!el){ console.log("[category] 容器不存在"); return; }
  el.innerHTML = "";
  console.log("[category] 请求大类分析:", y, m);
  loadCategoryAnalysis(y, m).then(function(cres){
    console.log("[category] 返回:", cres ? (cres.monthly_category_breakdown ? "有breakdown" : "无breakdown") : "null");
    if(cres && cres.monthly_category_breakdown){
      el.innerHTML = buildCategoryMonthlyHtml(cres, y, m);
      console.log("[category] 渲染完成, 长度:", el.innerHTML.length);
    }
  }).catch(function(err){ console.error("[category] 请求失败:", err); });
}

/* 构建消费大类/细类明细 HTML（analyze_category_monthly.py 脚本结果） */
function buildCategoryMonthlyHtml(cres, y, m){
  var breakdown = cres.monthly_category_breakdown;
  var ym = y + "-" + pad2m(m);
  var monthData = null;
  var list = breakdown.monthly || [];
  for(var i=0;i<list.length;i++){
    if(list[i].month === ym){ monthData = list[i]; break; }
  }
  console.log("[category] 目标月份:", ym, "脚本月份:", list.map(function(x){return x.month;}));
  if(!monthData){ console.log("[category] 未匹配到该月数据"); return ""; }

  var cats = monthData.categories || [];
  var html = '<div class="month-analysis">'+
    '<div class="ma-title">消费大类 / 细类（'+ym+'）</div>';
  if(!cats.length){
    html += '<div class="ma-empty">本月无支出明细</div></div>';
    return html;
  }
  html += '<div class="cat-list">';
  cats.forEach(function(c){
    var pct = c.percentage || "0%";
    var subs = c.subcategories || [];
    var hasSub = subs.length > 0;
    var arrow = hasSub ? '<span class="cat-arrow">▸</span>' : '';
    html += '<div class="cat-row'+(hasSub?'':' cat-no-sub')+'"'+(hasSub?' onclick="toggleSubcats(this)"':'')+'>'+
      '<div class="cat-row-head">'+
        arrow+
        '<span class="cat-name">'+c.category+'</span>'+
        '<span class="cat-amt exp">'+fmtMoney(c.amount)+'</span>'+
        '<span class="cat-pct">'+pct+'</span>'+
        '<span class="cat-cnt">'+c.count+'笔</span>'+
      '</div>';
    // 细类（默认折叠）
    if(hasSub){
      html += '<div class="subcat-list collapsed">';
      subs.forEach(function(sc){
        html += '<div class="subcat-row">'+
          '<span class="subcat-name">'+sc.subcategory+'</span>'+
          '<span class="subcat-amt exp">'+fmtMoney(sc.amount)+'</span>'+
          '<span class="subcat-cnt">'+(sc.count||0)+'笔</span>'+
          '<span class="subcat-pct">'+sc.percentage+'</span>'+
        '</div>';
      });
      html += '</div>';
    }
    html += '</div>';
  });
  html += '</div></div>';
  return html;
}

/* 点击大类展开/折叠细类 */
function toggleSubcats(rowEl){
  var sub = rowEl.querySelector ? rowEl.querySelector(".subcat-list") : null;
  if(!sub) return;
  var collapsed = sub.classList.toggle("collapsed");
  var arrow = rowEl.querySelector ? rowEl.querySelector(".cat-arrow") : null;
  if(arrow) arrow.textContent = collapsed ? "▸" : "▾";
}

/* 兜底：脚本接口不可用时，用本地 records 按消费类型分三层，避免本月概览空白 */
function renderMonthStatsLocal(y, m){
  var el = document.getElementById("monthStats");
  var recs = getRecords();
  function inM(dateStr){ return isInMonth(dateStr, y, m); }
  function expInM(){ return recs.filter(function(r){ return isExpense(r) && inM(r.date); }); }

  var monthIncome = recs.filter(function(r){ return isIncome(r) && inM(r.date); }).reduce(function(s,r){ return s+r.amount; },0);
  var monthExpenses = expInM();
  var monthExpense = monthExpenses.reduce(function(s,r){ return s+r.amount; },0);
  var balance = monthIncome - monthExpense;
  var monthLabel = y + "年" + m + "月";

  // 按消费类型（expenseType）分三层：刚性固定/刚性必要/弹性支出
  var rigidFixed = 0, rigidNecessary = 0, flexible = 0;
  monthExpenses.forEach(function(r){
    var t = (r.expenseType || "").trim();
    if(t === "刚性固定") rigidFixed += r.amount;
    else if(t === "刚性必要") rigidNecessary += r.amount;
    else flexible += r.amount;
  });

  el.innerHTML = [
    { label:monthLabel+"收入", val: fmtMoney(monthIncome), cls:"income", sub:"本地数据" },
    { label:"总支出", val: fmtMoney(monthExpense), cls:"expense", sub:"固定 "+fmtMoney(rigidFixed)+" / 必要 "+fmtMoney(rigidNecessary)+" / 弹性 "+fmtMoney(flexible) },
    { label:"弹性支出", val: fmtMoney(flexible), cls:"expense", sub:"本地数据" },
    { label:"本月结余", val: fmtMoney(balance), cls: balance>=0?"income":"expense", sub: balance>=0?"盈余":"超支" }
  ].map(function(s){
    return '<div class="stat-card">'+
      '<div class="stat-label">'+s.label+'</div>'+
      '<div class="stat-val '+s.cls+'">'+s.val+'</div>'+
      '<div class="stat-sub">'+(s.sub||"")+'</div>'+
    '</div>';
  }).join("");
}

function rate(v){ return (v==null || v==="") ? "0%" : v; }
function pad2m(n){ return String(n).padStart(2,"0"); }

function renderRecentRecords(){
  var recs = getRecords().slice(0, 4);
  var el = document.getElementById("recentRecords");
  if(recs.length === 0){
    el.innerHTML = '<div class="empty">'+ICON.check+'<div>还没有记录，去记一笔吧</div></div>';
    return;
  }
  el.innerHTML = recs.map(function(r){
    var cfg = CATS[r.category] || CATS["其他"];
    var sign = isIncome(r) ? "+" : "-";
    return '<div class="record-item">'+
      '<div class="record-icon" style="background:'+cfg.color+'15;color:'+cfg.color+'">'+cfg.icon+'</div>'+
      '<div class="record-info">'+
        '<div class="record-cat">'+(r.demo?'<span style="color:var(--gold);font-size:10px;">[示例]</span> ':'')+(r.itemName||r.category)+'</div>'+
        '<div class="record-note">'+(r.subcategory?r.category+' · '+r.subcategory:r.category)+'</div>'+
      '</div>'+
      '<div style="text-align:right">'+
        '<div class="record-amt '+(isIncome(r)?"income":"expense")+'">'+sign+fmtMoney(r.amount)+'</div>'+
      '</div>'+
    '</div>';
  }).join("");
}
