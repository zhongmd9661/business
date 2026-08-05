// ===== 内部单位通信录管理 =====
let INTERNAL_UNITS_DATA = [];

function getAuthHeaders() {
  const token = localStorage.getItem("auth_token");
  if (!token) {
    alert("请先登录");
    return null;
  }
  return { "Authorization": "Bearer " + token };
}

async function loadInternalUnits() {
  const tbody = document.getElementById("internal-units-tbody");
  if (!tbody) return;
  const auth = getAuthHeaders();
  if (!auth) return;
  tbody.innerHTML = '<tr><td colspan="4" style="padding:40px;text-align:center;">加载中...</td></tr>';
  try {
    const resp = await fetch("/api/admin/internal-units", { headers: auth });
    if (!resp.ok) {
      const txt = await resp.text();
      throw new Error("HTTP " + resp.status + ": " + txt);
    }
    INTERNAL_UNITS_DATA = await resp.json();
    renderInternalUnits(INTERNAL_UNITS_DATA);
  } catch (e) {
    console.error("[InternalUnits] load failed:", e);
    tbody.innerHTML = '<tr><td colspan="4" style="padding:40px;text-align:center;color:#ef4444;">加载失败: ' + e.message + "</td></tr>";
  }
}

function renderInternalUnits(units) {
  const tbody = document.getElementById("internal-units-tbody");
  const info = document.getElementById("units-count-info");
  if (!units.length) {
    tbody.innerHTML = '<tr><td colspan="4" style="padding:40px;text-align:center;color:#6b7280;">暂无数据，请导入 Excel 文件</td></tr>';
    if (info) info.textContent = "";
    return;
  }
  const activeCount = units.filter(function (u) {
    return u.status === "active";
  }).length;
  if (info) info.textContent = activeCount + " 个启用 / " + units.length + " 个总计";

  let html = "";
  for (let idx = 0; idx < units.length; idx++) {
    const u = units[idx];
    const badge =
      u.status === "active"
        ? '<span style="background:#dcfce7;color:#166534;padding:2px 10px;border-radius:4px;font-size:12px;font-weight:600;">启用</span>'
        : '<span style="background:#fee2e2;color:#991b1b;padding:2px 10px;border-radius:4px;font-size:12px;font-weight:600;">停用</span>';
    const toggleText = u.status === "active" ? "停用" : "启用";
    const toggleColor = u.status === "active" ? "#ef4444" : "#10b981";
    const newStatus = u.status === "active" ? "deleted" : "active";

    html += '<tr style="border-bottom:1px solid #f3f4f6;">';
    html += '<td style="padding:8px 12px;color:#6b7280;">' + (idx + 1) + "</td>";
    html += '<td style="padding:8px 12px;">' + u.name + "</td>";
    html += '<td style="padding:8px 12px;text-align:center;">' + badge + "</td>";
    html += '<td style="padding:8px 12px;text-align:center;">';
    html +=
      '<button class="action-btn" style="font-size:12px;padding:4px 10px;color:' +
      toggleColor +
      ';border-color:' +
      toggleColor +
      ';" data-action="toggle" data-id="' +
      u.id +
      '" data-status="' +
      newStatus +
      '">' +
      toggleText +
      "</button> ";
    html +=
      '<button class="action-btn" style="font-size:12px;padding:4px 10px;color:#ef4444;" data-action="delete" data-id="' +
      u.id +
      '" data-name="' +
      u.name +
      '">删除</button>';
    html += "</td></tr>";
  }
  tbody.innerHTML = html;

  tbody.querySelectorAll('[data-action="toggle"]').forEach(function (btn) {
    btn.addEventListener("click", function () {
      toggleUnitStatus(parseInt(this.dataset.id), this.dataset.status);
    });
  });
  tbody.querySelectorAll('[data-action="delete"]').forEach(function (btn) {
    btn.addEventListener("click", function () {
      deleteUnit(parseInt(this.dataset.id), this.dataset.name);
    });
  });
}

function filterInternalUnits() {
  const keyword = document.getElementById("units-search-input").value.toLowerCase();
  const sf = document.getElementById("units-status-filter").value;
  let filtered = INTERNAL_UNITS_DATA.filter(function (u) {
    if (keyword && !u.name.toLowerCase().includes(keyword)) return false;
    if (sf && u.status !== sf) return false;
    return true;
  });
  renderInternalUnits(filtered);
}

async function toggleUnitStatus(id, newStatus) {
  const txt = newStatus === "active" ? "启用" : "停用";
  if (!confirm("确定要" + txt + "该单位吗？")) return;
  const auth = getAuthHeaders();
  if (!auth) return;
  try {
    const resp = await fetch("/api/admin/internal-units/" + id, {
      method: "PUT",
      headers: Object.assign({}, auth, { "Content-Type": "application/json" }),
      body: JSON.stringify({ status: newStatus }),
    });
    if (!resp.ok) throw new Error("操作失败");
    showToast("\u2705 已" + txt);
    loadInternalUnits();
  } catch (e) {
    alert("操作失败: " + e.message);
  }
}

async function deleteUnit(id, name) {
  if (!confirm('确定要永久删除 "' + name + '" 吗？')) return;
  const auth = getAuthHeaders();
  if (!auth) return;
  try {
    const resp = await fetch("/api/admin/internal-units/" + id, {
      method: "DELETE",
      headers: auth,
    });
    if (!resp.ok) throw new Error("删除失败");
    showToast("\u2705 已删除");
    loadInternalUnits();
  } catch (e) {
    alert("删除失败: " + e.message);
  }
}

async function importInternalUnits(event) {
  const file = event.target.files[0];
  if (!file) return;
  const auth = getAuthHeaders();
  if (!auth) return;
  try {
    const fd = new FormData();
    fd.append("file", file);
    const resp = await fetch("/api/admin/internal-units/import", {
      method: "POST",
      headers: auth,
      body: fd,
    });
    if (!resp.ok) {
      const txt = await resp.text();
      throw new Error("HTTP " + resp.status + ": " + txt);
    }
    const r = await resp.json();
    alert(
      "\u5bfc\u5165\u5b8c\u6210\uFF01\n\u603B\u8BA1:" +
        r.total_rows +
        "\u884C \u65B0\u589E:" +
        r.added +
        " \u66F4\u65B0:" +
        r.updated +
        " \u505C\u7528:" +
        r.deleted +
        " \u5FFD\u7565:" +
        r.ignored
    );
    loadInternalUnits();
  } catch (e) {
    console.error("[Import Error]", e.message);
    alert("\u5BFC\u5165\u5931\u8D25: " + e.message);
  }
  event.target.value = "";
}

async function exportInternalUnits() {
  const auth = getAuthHeaders();
  if (!auth) return;
  try {
    const resp = await fetch("/api/admin/internal-units/export", {
      headers: auth,
    });
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "internal_units.xlsx";
    a.click();
    URL.revokeObjectURL(url);
    showToast("\u2705 \u5BFC\u51FA\u6210\u529F");
  } catch (e) {
    alert("\u5BFC\u51FA\u5931\u8D25: " + e.message);
  }
}

function downloadInternalUnitsTemplate() {
  const a = document.createElement("a");
  a.href = "/api/admin/internal-units/template";
  a.download = "\u5185\u90E8\u5355\u4F4D\u5BFC\u5165\u6A21\u677F.xlsx";
  a.click();
}

function openInternalUnitsModal() {
  document.getElementById("internal-units-modal").classList.add("active");
  loadInternalUnits();
}

function closeInternalUnitsModal() {
  document.getElementById("internal-units-modal").classList.remove("active");
}
