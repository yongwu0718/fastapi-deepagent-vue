"use strict";
/* ================================================================
 * 打工人小账本 · 收支日历
 * 月历展示：每个日期格子显示当日支出/收入对比
 * 点击某天 -> 跳转查看当日收支详情
 * ================================================================ */

var calYear = 0;
var calMonth = 0;         // 1-12
var calSelectedDate = ""; // 选中的日期 YYYY-MM-DD

function pad2(n){ return String(n).padStart(2,"0"); }

/* 初始化并渲染当前月 */
function renderCalendar(){
  var now = new Date();
  calYear = now.getFullYear();
  calMonth = now.getMonth() + 1;
  drawCalendar();
}

/* 按 date 字符串（YYYY-MM-DD）归集某天的支出与收入 */
function dayStats(dateStr){
  var recs = getRecords().filter(function(r){ return String(r.date) === dateStr; });
  var exp = 0, inc = 0;
  recs.forEach(function(r){
    if(isExpense(r)) exp += r.amount;
    else if(isIncome(r)) inc += r.amount;
  });
  return { exp: exp, inc: inc };
}

/* 按 date 字符串（YYYY-MM-DD）取出当天的记录明细 */
function dayRecords(dateStr){
  return getRecords().filter(function(r){ return String(r.date) === dateStr; });
}

/* 绘制当前月历 */
function drawCalendar(){
  document.getElementById("calTitle").textContent = calYear + "年" + calMonth + "月";

  var firstDow = new Date(calYear, calMonth - 1, 1).getDay();  // 当月1号是周几(0=周日)
  var daysInMonth = new Date(calYear, calMonth, 0).getDate();  // 当月天数

  var today = todayStr();
  var todayTag = calYear + "-" + pad2(calMonth);  // 当月前缀 YYYY-MM
  var selInMonth = (calSelectedDate || "").indexOf(todayTag) === 0;

  var html = "";
  // 当月1号前的空位
  for(var i = 0; i < firstDow; i++){
    html += '<div class="cal-cell cal-empty"></div>';
  }
  // 日期格子
  for(var d = 1; d <= daysInMonth; d++){
    var dateStr = todayTag + "-" + pad2(d);
    var st = dayStats(dateStr);
    var cls = "cal-cell";
    if(dateStr === today) cls += " today";
    if(selInMonth && dateStr === calSelectedDate) cls += " selected";
    html += '<div class="' + cls + '" onclick="calSelectDay(\'' + dateStr + '\')">' +
      '<div class="cal-day">' + d + '</div>' +
      '<div class="cal-stats">' +
        (st.exp > 0 ? '<div class="cal-exp">-'+fmtMoney(st.exp)+'</div>' : '') +
        (st.inc > 0 ? '<div class="cal-inc">+'+fmtMoney(st.inc)+'</div>' : '') +
        (st.exp === 0 && st.inc === 0 ? '<div class="cal-none">·</div>' : '') +
      '</div>' +
    '</div>';
  }

  document.getElementById("calGrid").innerHTML = html;

  // 若选中日不在当前月，清空详情；否则同步刷新选中日详情
  if(!selInMonth){
    calSelectedDate = "";
    var det = document.getElementById("calDayDetail");
    if(det) det.innerHTML = "";
  } else if(calSelectedDate){
    renderDayDetail(calSelectedDate);
  }
}

/* 点击某一天：跳转查看当日收支详情 */
function calSelectDay(dateStr){
  calSelectedDate = dateStr;
  drawCalendar();   // 重绘以高亮选中日并刷新详情
}

/* 渲染选中日的收支详情 */
function renderDayDetail(dateStr){
  var el = document.getElementById("calDayDetail");
  var recs = dayRecords(dateStr);
  var exp = 0, inc = 0;
  var expList = [], incList = [];
  recs.forEach(function(r){
    if(isExpense(r)){
      exp += r.amount;
      expList.push(r);
    } else if(isIncome(r)){
      inc += r.amount;
      incList.push(r);
    }
  });

  var parts = dateStr.split("-");
  var title = parts[0] + "年" + parseInt(parts[1],10) + "月" + parseInt(parts[2],10) + "日";
  var balance = inc - exp;

  var html = '<div class="cal-detail">' +
    '<div class="cal-detail-head">' +
      '<span class="cal-detail-title">' + title + ' 收支详情</span>' +
    '</div>' +
    '<div class="cal-detail-total">' +
      '<div class="cd-stat"><span class="cd-label">收入</span><span class="cd-val inc">+' + fmtMoney(inc) + '</span></div>' +
      '<div class="cd-stat"><span class="cd-label">支出</span><span class="cd-val exp">-' + fmtMoney(exp) + '</span></div>' +
      '<div class="cd-stat"><span class="cd-label">结余</span><span class="cd-val ' + (balance>=0?'inc':'exp') + '">' + (balance>=0?'+':'') + fmtMoney(balance) + '</span></div>' +
    '</div>';

  // 支出明细
  html += '<div class="cd-sec">' +
    '<div class="cd-sec-title">支出 <span class="cd-sec-count">' + expList.length + '</span></div>' +
    (expList.length ? expList.map(recRowHtml).join("") : '<div class="cd-empty">当日无支出</div>') +
  '</div>';

  // 收入明细
  html += '<div class="cd-sec">' +
    '<div class="cd-sec-title">收入 <span class="cd-sec-count">' + incList.length + '</span></div>' +
    (incList.length ? incList.map(recRowHtml).join("") : '<div class="cd-empty">当日无收入</div>') +
  '</div>';

  html += '</div>';
  el.innerHTML = html;
}

/* 单条记录行 */
function recRowHtml(r){
  var cfg = CATS[r.category] || CATS["其他"];
  var name = r.itemName || (r.subcategory ? r.subcategory : r.category);
  var isExp = isExpense(r);
  var sign = isExp ? "-" : "+";
  var sub = r.subcategory ? r.category + " · " + r.subcategory : r.category;
  return '<div class="cd-item">' +
    '<div class="cd-item-icon" style="background:'+cfg.color+'15;color:'+cfg.color+'">' + cfg.icon + '</div>' +
    '<div class="cd-item-info">' +
      '<div class="cd-item-name">' + name + '</div>' +
      '<div class="cd-item-sub">' + sub + '</div>' +
    '</div>' +
    '<div class="cd-item-amt ' + (isExp?'exp':'inc') + '">' + sign + fmtMoney(r.amount) + '</div>' +
  '</div>';
}

/* 上个月 */
function calPrevMonth(){
  calMonth--;
  if(calMonth < 1){ calMonth = 12; calYear--; }
  drawCalendar();
  renderMonthStats(calYear, calMonth);   // 本月概览跟随日历月份
}

/* 下个月 */
function calNextMonth(){
  calMonth++;
  if(calMonth > 12){ calMonth = 1; calYear++; }
  drawCalendar();
  renderMonthStats(calYear, calMonth);   // 本月概览跟随日历月份
}
