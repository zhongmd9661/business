
    // ===== 人员级别标准数据 =====
    const DEFAULT_STANDARDS = {
      external: [
        { level: '省管中层', externalBanquet: '≤400元/人·次', externalGift: '≤400元/人·次', otherBanquet: '≤200元/人·次', alcohol: '白酒≤400元/500ml，红酒≤400元/750ml' },
        { level: '市管中层', externalBanquet: '≤300元/人·次', externalGift: '≤300元/人·次', otherBanquet: '≤200元/人·次', alcohol: '白酒≤300元/500ml，红酒≤300元/750ml' },
        { level: '其他人员', externalBanquet: '≤200元/人·次', externalGift: '≤200元/人·次', otherBanquet: '≤150元/人·次', alcohol: '白酒≤200元/500ml，红酒≤200元/750ml' },
      ],
      internal: [
        { subject: '省管中层经理', standard: '≤150元/人·次', note: '不得进行商务宴请，不上烟酒、不得赠送纪念品' },
        { subject: '市管中层经理', standard: '≤150元/人·次', note: '不得进行商务宴请，不上烟酒、不得赠送纪念品' },
        { subject: '其他人员', standard: '≤100元/人·次', note: '不得进行商务宴请，不上烟酒、不得赠送纪念品' },
      ],
      workmeal: [
        { scene: '单位食堂', standard: '参照食堂正常标准或差旅伙食补贴', note: '优先自助形式，不上烟酒' },
        { scene: '外出调研无法在食堂用餐', standard: '参照上述标准就近安排', note: '出差人员已领差旅伙食补贴的应交纳费用' },
      ],
      gift: [
        { level: '省管中层', externalGift: '≤400元/人·次', otherGift: '不得赠送' },
        { level: '市管中层', externalGift: '≤300元/人·次', otherGift: '不得赠送' },
        { level: '其他人员', externalGift: '≤200元/人·次', otherGift: '不得赠送' },
      ],
      accompany: [
        { type: '对外业务招待', count: '≤5人', limit: '可对等' },
        { type: '对外业务招待', count: '>5人', limit: '不超过招待对象超过部分的二分之一' },
        { type: '内部业务招待', count: '≤10人', limit: '≤3人' },
        { type: '内部业务招待', count: '>10人', limit: '不超过招待对象的三分之一' },
      ]
    };

    let STANDARDS_DATA = {};
    try {
      const saved = localStorage.getItem('audit-standards-custom');
      if (saved) {
        const data = JSON.parse(saved);
        if (data.external) STANDARDS_DATA.external = data.external;
        if (data.internal) STANDARDS_DATA.internal = data.internal;
        if (data.workmeal) STANDARDS_DATA.workmeal = data.workmeal;
        if (data.gift) STANDARDS_DATA.gift = data.gift;
        if (data.accompany) STANDARDS_DATA.accompany = data.accompany;
      }
    } catch (e) {}
    if (!STANDARDS_DATA.external) STANDARDS_DATA.external = DEFAULT_STANDARDS.external;
    if (!STANDARDS_DATA.internal) STANDARDS_DATA.internal = DEFAULT_STANDARDS.internal;
    if (!STANDARDS_DATA.workmeal) STANDARDS_DATA.workmeal = DEFAULT_STANDARDS.workmeal;
    if (!STANDARDS_DATA.gift) STANDARDS_DATA.gift = DEFAULT_STANDARDS.gift;
    if (!STANDARDS_DATA.accompany) STANDARDS_DATA.accompany = DEFAULT_STANDARDS.accompany;

    // ===== 场景切换 =====
    function selectScenario(scenario) {
      // Update buttons
      document.querySelectorAll('.scenario-btn').forEach(btn => btn.classList.remove('active'));
      event.currentTarget.classList.add('active');

      // Update cards
      document.querySelectorAll('.scenario-card').forEach(card => card.classList.remove('active'));
      document.getElementById('scenario-' + scenario).classList.add('active');
    }

    // ===== 人员级别自动关联标准 =====
    function onLevelChange(scenario) {
      const radio = document.querySelector('input[name="scenario-' + scenario + '-level"]:checked');
      const levelHint = document.getElementById('scenario-' + scenario + '-level-hint');
      if (!levelHint) return;

      const level = radio ? radio.value : '';
      if (!level) {
        levelHint.innerHTML = '';
        return;
      }

      let standard = null;
      let scenarioType = '';

      switch (scenario) {
        case 'A':
        case 'B':
          standard = STANDARDS_DATA.external.find(s => s.level === level);
          scenarioType = '外事/商务';
          break;
        case 'C':
          standard = STANDARDS_DATA.external.find(s => s.level === level);
          scenarioType = '其他公务';
          break;
        case 'D':
          standard = STANDARDS_DATA.internal.find(s => s.subject === level);
          scenarioType = '内部业务';
          break;
        case 'E':
          standard = STANDARDS_DATA.workmeal.find(s => s.scene === '单位食堂');
          scenarioType = '工作餐';
          break;
        case 'F':
          standard = STANDARDS_DATA.external.find(s => s.level === '省管中层');
          scenarioType = '党政军机关';
          break;
      }

      if (!standard) return;

      if (scenario === 'A' || scenario === 'B') {
        const stdCapita = document.getElementById('scenario-' + scenario + '-std-capita');
        const stdBaijiu = document.getElementById('scenario-' + scenario + '-std-baijiu');
        const stdWine = document.getElementById('scenario-' + scenario + '-std-wine');
        const stdGift = document.getElementById('scenario-' + scenario + '-std-gift');

        if (stdCapita) stdCapita.innerHTML = '<span class="std-number">' + standard.externalBanquet + '</span>';
        if (stdBaijiu) stdBaijiu.innerHTML = '<span class="std-number">' + standard.alcohol.split('，')[0] + '</span>';
        if (stdWine) stdWine.innerHTML = '<span class="std-number">' + standard.alcohol.split('，')[1] + '</span>';
        if (stdGift) stdGift.innerHTML = '<span class="std-number">' + standard.externalGift + '</span>';

        levelHint.innerHTML = '<span class="form-hint success">✓ 已关联标准</span>';

        const alcoholLimit = document.getElementById('scenario-' + scenario + '-alcohol-limit');
        const alcoholStd = document.getElementById('scenario-' + scenario + '-alcohol-std');
        if (alcoholLimit && alcoholStd) {
          alcoholStd.textContent = standard.alcohol;
          alcoholLimit.innerHTML = '标准：<span class="form-hint accent">' + standard.alcohol + '</span>';
        }

      } else if (scenario === 'C') {
        const stdCapita = document.getElementById('scenario-' + scenario + '-std-capita');
        const stdBaijiu = document.getElementById('scenario-' + scenario + '-std-baijiu');
        const stdWine = document.getElementById('scenario-' + scenario + '-std-wine');
        const stdGift = document.getElementById('scenario-' + scenario + '-std-gift');

        if (stdCapita) stdCapita.innerHTML = '<span class="std-number">' + standard.otherBanquet + '</span>';
        if (stdBaijiu) stdBaijiu.innerHTML = '<span class="std-number">≤100元/瓶</span>';
        if (stdWine) stdWine.innerHTML = '<span class="std-number">≤100元/瓶</span>';
        if (stdGift) stdGift.innerHTML = '<span class="std-number">不得赠送</span>';

        levelHint.innerHTML = '<span class="form-hint warning">⚠️ 注意：其他公务招待不得赠送纪念品</span>';

        const alcoholLimit = document.getElementById('scenario-' + scenario + '-alcohol-limit');
        const alcoholStd = document.getElementById('scenario-' + scenario + '-alcohol-std');
        if (alcoholLimit && alcoholStd) {
          alcoholStd.textContent = '≤100元/瓶';
          alcoholLimit.innerHTML = '标准：<span class="form-hint warning">≤100元/瓶</span>';
        }

      } else if (scenario === 'D') {
        const stdCapita = document.getElementById('scenario-' + scenario + '-std-capita');
        const stdBaijiu = document.getElementById('scenario-' + scenario + '-std-baijiu');
        const stdWine = document.getElementById('scenario-' + scenario + '-std-wine');
        const stdGift = document.getElementById('scenario-' + scenario + '-std-gift');
        const levelDisplay = document.getElementById('scenario-' + scenario + '-level-display');

        if (stdCapita) stdCapita.innerHTML = '<span class="std-number">' + standard.standard + '</span>';
        if (stdBaijiu) stdBaijiu.innerHTML = '<span class="std-number">不得提供</span>';
        if (stdWine) stdWine.innerHTML = '<span class="std-number">不得提供</span>';
        if (stdGift) stdGift.innerHTML = '<span class="std-number">不得赠送</span>';

        if (levelDisplay) levelDisplay.textContent = level;

        levelHint.innerHTML = '<span class="form-hint warning">⚠️ 注意：内部招待不得赠送纪念品，不上烟酒</span>';

        const alcoholLimit = document.getElementById('scenario-' + scenario + '-alcohol-limit');
        const alcoholStd = document.getElementById('scenario-' + scenario + '-alcohol-std');
        if (alcoholLimit && alcoholStd) {
          alcoholStd.textContent = '不得提供';
          alcoholLimit.innerHTML = '标准：<span class="form-hint error">不得提供</span>';
        }

      } else if (scenario === 'E') {
        const stdCapita = document.getElementById('scenario-' + scenario + '-std-capita');
        const stdBaijiu = document.getElementById('scenario-' + scenario + '-std-baijiu');
        const stdWine = document.getElementById('scenario-' + scenario + '-std-wine');
        const stdGift = document.getElementById('scenario-' + scenario + '-std-gift');

        if (stdCapita) stdCapita.innerHTML = '<span class="std-number">≤60元/人</span>';
        if (stdBaijiu) stdBaijiu.innerHTML = '<span class="std-number">不得提供</span>';
        if (stdWine) stdWine.innerHTML = '<span class="std-number">不得提供</span>';
        if (stdGift) stdGift.innerHTML = '<span class="std-number">不得赠送</span>';

        levelHint.innerHTML = '<span class="form-hint warning">⚠️ 注意：工作餐不上烟酒，不得赠送纪念品</span>';

        const alcoholLimit = document.getElementById('scenario-' + scenario + '-alcohol-limit');
        const alcoholStd = document.getElementById('scenario-' + scenario + '-alcohol-std');
        if (alcoholLimit && alcoholStd) {
          alcoholStd.textContent = '不得提供';
          alcoholLimit.innerHTML = '标准：<span class="form-hint error">不得提供</span>';
        }

      } else if (scenario === 'F') {
        const stdBaijiu = document.getElementById('scenario-' + scenario + '-std-baijiu');
        const stdWine = document.getElementById('scenario-' + scenario + '-std-wine');
        const stdGift = document.getElementById('scenario-' + scenario + '-std-gift');

        if (stdBaijiu) stdBaijiu.innerHTML = '<span class="std-number">严禁提供</span>';
        if (stdWine) stdWine.innerHTML = '<span class="std-number">严禁提供</span>';
        if (stdGift) stdGift.innerHTML = '<span class="std-number">严禁赠送</span>';

        levelHint.innerHTML = '<span class="form-hint error">❌ 严禁提供酒水、严禁赠送纪念品</span>';

        const alcoholLimit = document.getElementById('scenario-' + scenario + '-alcohol-limit');
        const alcoholStd = document.getElementById('scenario-' + scenario + '-alcohol-std');
        if (alcoholLimit && alcoholStd) {
          alcoholStd.textContent = '严禁提供';
          alcoholLimit.innerHTML = '标准：<span class="form-hint error">严禁提供</span>';
        }
      }
    }

    // ===== 陪餐人数自动计算 =====
    function calculateAccompanying(type, guests) {
      guests = Math.max(0, Math.floor(guests));
      if (guests <= 0) return { max: 0, formula: '招待人数为0，无需陪餐' };

      if (type === 'external') {
        if (guests <= 5) {
          return { max: guests, formula: '≤' + guests + '人（招待对象≤5人，陪餐可对等）' };
        } else {
          const max = 5 + Math.floor((guests - 5) / 2);
          return { max: max, formula: '≤' + max + '人（招待对象>5人，陪餐≤5+(招待对象-5)/2）' };
        }
      } else {
        if (guests <= 10) {
          return { max: 3, formula: '≤3人（招待对象≤10人，陪餐≤3）' };
        } else {
          const max = Math.floor(guests / 3);
          return { max: max, formula: '≤' + max + '人（招待对象>10人，陪餐≤招待对象/3）' };
        }
      }
    }

    function onGuestsChange(scenario, type) {
      const guestsInput = document.getElementById('scenario-' + scenario + '-guests');
      const accompanyInput = document.getElementById('scenario-' + scenario + '-accompany-count');
      const hintSpan = document.getElementById('scenario-' + scenario + '-accompany-hint');
      if (!guestsInput || !accompanyInput || !hintSpan) return;

      const guests = parseInt(guestsInput.value) || 0;
      const result = calculateAccompanying(type, guests);

      hintSpan.innerHTML = '<span class="form-hint accent">陪餐上限：' + result.max + '人</span> &nbsp; <span style="font-size:10px;color:var(--color-text-secondary);">(' + result.formula + ')</span>';

      const currentAccompany = parseInt(accompanyInput.value) || 0;
      if (currentAccompany > result.max && currentAccompany > 0) {
        hintSpan.innerHTML += ' <span class="form-hint error">⚠️ 超标！</span>';
      }
    }

    // ===== 费用自动计算 =====
    function calculateScenarioA() {
      const perCapita = parseFloat(document.getElementById('scenario-A-per-capita').value) || 0;
      const guests = parseInt(document.getElementById('scenario-A-guests').value) || 0;
      const baijiuPrice = parseFloat(document.getElementById('scenario-A-baijiu-price').value) || 0;
      const winePrice = parseFloat(document.getElementById('scenario-A-wine-price').value) || 0;
      const giftPer = parseFloat(document.getElementById('scenario-A-gift-per').value) || 0;
      const rooms = parseInt(document.getElementById('scenario-A-rooms').value) || 0;
      const roomPrice = parseFloat(document.getElementById('scenario-A-room-price').value) || 0;

      const mealTotal = perCapita * guests;
      const alcoholTotal = (baijiuPrice * 0.5 + winePrice * 0.75) * guests;
      const giftTotal = giftPer * guests;
      const roomTotal = rooms * roomPrice;
      const total = mealTotal + alcoholTotal + giftTotal + roomTotal;
      const per = guests > 0 ? total / guests : 0;

      document.getElementById('scenario-A-meal-total').textContent = '¥' + mealTotal.toFixed(2);
      document.getElementById('scenario-A-gift-total').textContent = '¥' + giftTotal.toFixed(2);
      document.getElementById('scenario-A-room-total').textContent = '¥' + roomTotal.toFixed(2);
      document.getElementById('scenario-A-summary-meal').textContent = '¥' + mealTotal.toFixed(2);
      document.getElementById('scenario-A-summary-alcohol').textContent = '¥' + alcoholTotal.toFixed(2);
      document.getElementById('scenario-A-summary-gift').textContent = '¥' + giftTotal.toFixed(2);
      document.getElementById('scenario-A-summary-room').textContent = '¥' + roomTotal.toFixed(2);
      document.getElementById('scenario-A-summary-total').textContent = '¥' + total.toFixed(2);
      document.getElementById('scenario-A-summary-per').textContent = '¥' + per.toFixed(2) + '/人';

      // Validate per-capita
      const level = document.querySelector('input[name="scenario-A-level"]:checked');
      if (level && perCapita > 0) {
        const std = STANDARDS_DATA.external.find(s => s.level === level.value);
        if (std) {
          const maxBanquet = parseInt(std.externalBanquet.replace(/[^\d]/g, ''));
          const status = document.getElementById('scenario-A-capita-status');
          if (perCapita > maxBanquet) {
            status.textContent = '⚠️ 超标！';
            status.className = 'form-hint error';
          } else {
            status.textContent = '✓ 未超标';
            status.className = 'form-hint success';
          }
        }
      }
    }

    function calculateScenarioB() {
      const perCapita = parseFloat(document.getElementById('scenario-B-per-capita').value) || 0;
      const guests = parseInt(document.getElementById('scenario-B-guests').value) || 0;
      const baijiuPrice = parseFloat(document.getElementById('scenario-B-baijiu-price').value) || 0;
      const winePrice = parseFloat(document.getElementById('scenario-B-wine-price').value) || 0;
      const giftPer = parseFloat(document.getElementById('scenario-B-gift-per').value) || 0;
      const rooms = parseInt(document.getElementById('scenario-B-rooms').value) || 0;
      const roomPrice = parseFloat(document.getElementById('scenario-B-room-price').value) || 0;

      const mealTotal = perCapita * guests;
      const alcoholTotal = (baijiuPrice * 0.5 + winePrice * 0.75) * guests;
      const giftTotal = giftPer * guests;
      const roomTotal = rooms * roomPrice;
      const total = mealTotal + alcoholTotal + giftTotal + roomTotal;
      const per = guests > 0 ? total / guests : 0;

      document.getElementById('scenario-B-meal-total').textContent = '¥' + mealTotal.toFixed(2);
      document.getElementById('scenario-B-gift-total').textContent = '¥' + giftTotal.toFixed(2);
      document.getElementById('scenario-B-room-total').textContent = '¥' + roomTotal.toFixed(2);
      document.getElementById('scenario-B-summary-meal').textContent = '¥' + mealTotal.toFixed(2);
      document.getElementById('scenario-B-summary-alcohol').textContent = '¥' + alcoholTotal.toFixed(2);
      document.getElementById('scenario-B-summary-gift').textContent = '¥' + giftTotal.toFixed(2);
      document.getElementById('scenario-B-summary-room').textContent = '¥' + roomTotal.toFixed(2);
      document.getElementById('scenario-B-summary-total').textContent = '¥' + total.toFixed(2);
      document.getElementById('scenario-B-summary-per').textContent = '¥' + per.toFixed(2) + '/人';

      const level = document.querySelector('input[name="scenario-B-level"]:checked');
      if (level && perCapita > 0) {
        const std = STANDARDS_DATA.external.find(s => s.level === level.value);
        if (std) {
          const maxBanquet = parseInt(std.externalBanquet.replace(/[^\d]/g, ''));
          const status = document.getElementById('scenario-B-capita-status');
          if (perCapita > maxBanquet) {
            status.textContent = '⚠️ 超标！';
            status.className = 'form-hint error';
          } else {
            status.textContent = '✓ 未超标';
            status.className = 'form-hint success';
          }
        }
      }
    }

    function calculateScenarioC() {
      const perCapita = parseFloat(document.getElementById('scenario-C-per-capita').value) || 0;
      const guests = parseInt(document.getElementById('scenario-C-guests').value) || 0;
      const baijiuPrice = parseFloat(document.getElementById('scenario-C-baijiu-price').value) || 0;
      const winePrice = parseFloat(document.getElementById('scenario-C-wine-price').value) || 0;

      const mealTotal = perCapita * guests;
      const alcoholTotal = (baijiuPrice * 0.5 + winePrice * 0.75) * guests;
      const total = mealTotal + alcoholTotal;
      const per = guests > 0 ? total / guests : 0;

      document.getElementById('scenario-C-meal-total').textContent = '¥' + mealTotal.toFixed(2);
      document.getElementById('scenario-C-summary-meal').textContent = '¥' + mealTotal.toFixed(2);
      document.getElementById('scenario-C-summary-alcohol').textContent = '¥' + alcoholTotal.toFixed(2);
      document.getElementById('scenario-C-summary-total').textContent = '¥' + total.toFixed(2);
      document.getElementById('scenario-C-summary-per').textContent = '¥' + per.toFixed(2) + '/人';

      const level = document.querySelector('input[name="scenario-C-level"]:checked');
      if (level && perCapita > 0) {
        const std = STANDARDS_DATA.external.find(s => s.level === level.value);
        if (std) {
          const maxBanquet = parseInt(std.otherBanquet.replace(/[^\d]/g, ''));
          const status = document.getElementById('scenario-C-capita-status');
          if (perCapita > maxBanquet) {
            status.textContent = '⚠️ 超标！';
            status.className = 'form-hint error';
          } else {
            status.textContent = '✓ 未超标';
            status.className = 'form-hint success';
          }
        }
      }
    }

    function calculateScenarioD() {
      const perCapita = parseFloat(document.getElementById('scenario-D-per-capita').value) || 0;
      const guests = parseInt(document.getElementById('scenario-D-guests').value) || 0;

      const mealTotal = perCapita * guests;
      const total = mealTotal;
      const per = guests > 0 ? total / guests : 0;

      document.getElementById('scenario-D-meal-total').textContent = '¥' + mealTotal.toFixed(2);
      document.getElementById('scenario-D-summary-meal').textContent = '¥' + mealTotal.toFixed(2);
      document.getElementById('scenario-D-summary-total').textContent = '¥' + total.toFixed(2);
      document.getElementById('scenario-D-summary-per').textContent = '¥' + per.toFixed(2) + '/人';

      const level = document.querySelector('input[name="scenario-D-level"]:checked');
      if (level && perCapita > 0) {
        const std = STANDARDS_DATA.internal.find(s => s.subject === level.value);
        if (std) {
          const maxBanquet = parseInt(std.standard.replace(/[^\d]/g, ''));
          const status = document.getElementById('scenario-D-capita-status');
          if (perCapita > maxBanquet) {
            status.textContent = '⚠️ 超标！';
            status.className = 'form-hint error';
          } else {
            status.textContent = '✓ 未超标';
            status.className = 'form-hint success';
          }
        }
      }
    }

    function calculateScenarioE() {
      const perCapita = parseFloat(document.getElementById('scenario-E-per-capita').value) || 0;
      const guests = parseInt(document.getElementById('scenario-E-guests').value) || 0;

      const mealTotal = perCapita * guests;
      const total = mealTotal;
      const per = guests > 0 ? total / guests : 0;

      document.getElementById('scenario-E-meal-total').textContent = '¥' + mealTotal.toFixed(2);
      document.getElementById('scenario-E-summary-meal').textContent = '¥' + mealTotal.toFixed(2);
      document.getElementById('scenario-E-summary-per').textContent = '¥' + per.toFixed(2) + '/人';

      // Validate per-capita for workmeal
      const status = document.getElementById('scenario-E-capita-status');
      if (perCapita > 60) {
        status.textContent = '⚠️ 超标！工作餐≤60元/人';
        status.className = 'form-hint error';
      } else if (perCapita > 0) {
        status.textContent = '✓ 未超标';
        status.className = 'form-hint success';
      }
    }

    // ===== 导出/保存 =====
    function getFormData(scenario) {
      const data = { scenario: scenario, timestamp: new Date().toISOString() };

      const fields = ['date', 'location', 'org', 'guests', 'accompanyPeople', 'accompanyCount', 'perCapita', 'baijiuPrice', 'winePrice', 'giftPer', 'rooms', 'roomPrice', 'reason'];
      fields.forEach(f => {
        const el = document.getElementById('scenario-' + scenario + '-' + f);
        if (el) data[f] = el.value;
      });

      if (scenario === 'B') {
        const el = document.getElementById('scenario-B-nationality');
        if (el) data.nationality = el.value;
      }
      if (scenario === 'E') {
        const el = document.getElementById('scenario-E-fee');
        if (el) data.fee = el.value;
      }

      return data;
    }

    function saveFormData() {
      const activeCard = document.querySelector('.scenario-card.active');
      if (!activeCard) return;
      const scenario = activeCard.id.replace('scenario-', '');
      const data = getFormData(scenario);
      localStorage.setItem('fill-scenario-' + scenario, JSON.stringify(data));
      showToast('✅ 场景' + scenario + ' 数据已保存至浏览器本地存储');
    }

    function loadFormData(scenario) {
      const saved = localStorage.getItem('fill-scenario-' + scenario);
      if (!saved) return;
      try {
        const data = JSON.parse(saved);
        const fields = ['date', 'location', 'org', 'guests', 'accompanyPeople', 'accompanyCount', 'perCapita', 'baijiuPrice', 'winePrice', 'giftPer', 'rooms', 'roomPrice', 'reason'];
        fields.forEach(f => {
          const el = document.getElementById('scenario-' + scenario + '-' + f);
          if (el && data[f]) el.value = data[f];
        });
        if (scenario === 'B' && data.nationality) {
          const el = document.getElementById('scenario-B-nationality');
          if (el) el.value = data.nationality;
        }
        if (scenario === 'E' && data.fee) {
          const el = document.getElementById('scenario-E-fee');
          if (el) el.value = data.fee;
        }
      } catch (e) {
        console.warn('Failed to load saved data:', e);
      }
    }

    function exportFormData() {
      const activeCard = document.querySelector('.scenario-card.active');
      if (!activeCard) return;
      const scenario = activeCard.id.replace('scenario-', '');
      const data = getFormData(scenario);
      const json = JSON.stringify(data, null, 2);
      const blob = new Blob([json], { type: 'application/json;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = '招待费场景' + scenario + '_' + new Date().toISOString().slice(0,10) + '.json';
      a.click();
      URL.revokeObjectURL(url);
      showToast('✅ 场景' + scenario + ' 数据已导出为JSON文件');
    }

    // ===== 提交记录 =====
    const SCENARIO_NAMES = {
      A: '商务招待', B: '外事招待', C: '其他公务招待',
      D: '内部业务招待', E: '工作餐', F: '党政军机关'
    };

    // ===== 企查查截图分析 =====
    let qichachaFile = null;
    let qichachaResultData = null;

    // ===== 参考模板 =====
    // ui资源 目录下的所有图片模板（硬编码，与 ui资源 目录保持同步）
    var BUILTIN_TEMPLATES = [
      { name: '企查查截图', path: 'ui资源/企查查截图.jpg' },
      { name: '企查查截图 - 副本', path: 'ui资源/企查查截图 - 副本.jpg' }
    ];

    function renderTemplates(templates) {
      const list = document.getElementById('qichachaTemplateList');
      if (!list) return;

      if (!templates || templates.length === 0) {
        list.innerHTML = '<span style="font-size:11px; color:var(--color-text-secondary);">暂无模板</span>';
        return;
      }

      let html = '';
      templates.forEach(function(t) {
        var displayName = t.name.replace(/\.[^.]+$/, '');
        html += `<span class="qichacha-template-preview" onclick="openTemplateLightbox('${t.path}')">
          <img src="${t.path}" alt="${escapeHtml(displayName)}">
          <span class="template-caption">${escapeHtml(displayName)}</span>
        </span>`;
      });
      list.innerHTML = html;
    }

    function loadTemplates() {
      fetch('/api/qichacha-templates')
        .then(function(r) { return r.json(); })
        .then(function(templates) {
          if (templates && templates.length > 0) {
            renderTemplates(templates);
          } else {
            renderTemplates(BUILTIN_TEMPLATES);
          }
        })
        .catch(function() {
          // 直接打开 HTML 文件时走本地回退
          renderTemplates(BUILTIN_TEMPLATES);
        });
    }

    function openTemplateLightbox(src) {
      var existing = document.getElementById('templateLightbox');
      if (existing) existing.remove();

      var overlay = document.createElement('div');
      overlay.id = 'templateLightbox';
      overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:2000;display:flex;align-items:center;justify-content:center;cursor:zoom-out;';
      overlay.onclick = function() { overlay.remove(); };

      // 按 ESC 关闭
      var escHandler = function(e) { if (e.key === 'Escape') { overlay.remove(); document.removeEventListener('keydown', escHandler); } };
      document.addEventListener('keydown', escHandler);

      // 注入闪烁动画（仅一次）
      if (!document.getElementById('lightbox-hint-style')) {
        var styleTag = document.createElement('style');
        styleTag.id = 'lightbox-hint-style';
        styleTag.textContent = '@keyframes hintFlash { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }';
        document.head.appendChild(styleTag);
      }

      // 关闭提示
      var hint = document.createElement('div');
      hint.style.cssText = 'position:fixed;top:24px;left:50%;transform:translateX(-50%);color:#fff;font-size:14px;font-family:var(--font-family);z-index:2001;background:rgba(0,0,0,0.55);padding:8px 20px;border-radius:20px;pointer-events:none;white-space:nowrap;animation: hintFlash 2s ease-in-out infinite;';
      hint.textContent = '按 ESC 或点击任意位置关闭';

      var img = document.createElement('img');
      img.src = src;
      img.style.cssText = 'max-width:90vw;max-height:90vh;object-fit:contain;border-radius:8px;box-shadow:0 8px 32px rgba(0,0,0,0.4);cursor:zoom-out;';

      overlay.appendChild(hint);
      overlay.appendChild(img);
      document.body.appendChild(overlay);
    }

    function handleQichachaUpload(event) {
      const file = event.target.files[0];
      if (!file) return;

      // Validate file type
      const allowed = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
      if (!allowed.includes(file.type)) {
        showToast('❌ 请上传 JPG/PNG 格式的图片');
        return;
      }

      // Validate file size (max 10MB)
      if (file.size > 10 * 1024 * 1024) {
        showToast('❌ 图片大小不能超过 10MB');
        return;
      }

      qichachaFile = file;
      qichachaResultData = null;

      // Show preview
      const reader = new FileReader();
      reader.onload = function(e) {
        const dropZone = document.getElementById('qichachaDropZone');
        dropZone.innerHTML = `<img src="${e.target.result}" alt="企查查截图"><input type="file" id="qichachaFileInput" accept="image/*" style="display:none" onchange="handleQichachaUpload(event)">`;
        dropZone.classList.add('has-image');

        // Enable analyze button
        document.getElementById('qichachaAnalyzeBtn').disabled = false;

        // Reset result card
        const resultCard = document.getElementById('qichachaResultCard');
        resultCard.className = 'qichacha-result-card pending';
        resultCard.innerHTML = `
          <div class="qichacha-result-row">
            <span class="qichacha-result-label">📋 状态</span>
            <span class="qichacha-result-value">已上传图片，请点击"开始识别"</span>
          </div>
        `;
      };
      reader.readAsDataURL(file);
    }

    // 处理剪贴板粘贴的图片
    function handlePastedImage(blob) {
      // Create a File object from the Blob
      const pastedFile = new File([blob], 'paste_' + Date.now() + '.png', { type: blob.type || 'image/png' });

      // Validate file size (max 10MB)
      if (pastedFile.size > 10 * 1024 * 1024) {
        showToast('❌ 图片大小不能超过 10MB');
        return;
      }

      qichachaFile = pastedFile;
      qichachaResultData = null;

      // Show preview
      const reader = new FileReader();
      reader.onload = function(e) {
        const dropZone = document.getElementById('qichachaDropZone');
        dropZone.innerHTML = `<img src="${e.target.result}" alt="企查查截图（粘贴）"><input type="file" id="qichachaFileInput" accept="image/*" style="display:none" onchange="handleQichachaUpload(event)">`;
        dropZone.classList.add('has-image');

        // Enable analyze button
        document.getElementById('qichachaAnalyzeBtn').disabled = false;

        // Reset result card
        const resultCard = document.getElementById('qichachaResultCard');
        resultCard.className = 'qichacha-result-card pending';
        resultCard.innerHTML = `
          <div class="qichacha-result-row">
            <span class="qichacha-result-label">📋 状态</span>
            <span class="qichacha-result-value">已粘贴截图，请点击"开始识别"</span>
          </div>
          <div style="margin-top:4px; font-size:11px; color:var(--color-success);">✅ 来自剪贴板</div>
        `;
      };
      reader.readAsDataURL(blob);

      showToast('✅ 已粘贴截图，点击"开始识别"');
    }

    function toggleOcrDeviceSelector() {
      const method = document.querySelector('input[name="qichacha-method"]:checked')?.value;
      const deviceSelector = document.getElementById('qichachaDeviceSelector');
      if (method === 'ocr') {
        deviceSelector.style.display = 'flex';
      } else {
        deviceSelector.style.display = 'none';
      }
    }

    async function analyzeQichacha() {
      if (!qichachaFile) {
        showToast('⚠️ 请先上传企查查截图');
        return;
      }

      const btn = document.getElementById('qichachaAnalyzeBtn');
      btn.disabled = true;
      btn.textContent = '⏳ 识别中...';

      const resultCard = document.getElementById('qichachaResultCard');
      resultCard.className = 'qichacha-result-card loading';
      resultCard.innerHTML = '<div style="text-align:center;padding:16px;"><div class="spinner" style="margin:0 auto 8px;"></div>正在识别企业经营状态...</div>';

      try {
        const methodRadio = document.querySelector('input[name="qichacha-method"]:checked');
        const method = methodRadio ? methodRadio.value : 'ocr';

        // 如果选的是 OCR，读取 device；否则默认 auto
        let device = 'auto';
        if (method === 'ocr') {
          const deviceRadio = document.querySelector('input[name="qichacha-device"]:checked');
          device = deviceRadio ? deviceRadio.value : 'auto';
        }

        const formData = new FormData();
        formData.append('file', qichachaFile);
        formData.append('method', method);
        formData.append('device', device);

        const response = await fetch('/api/qichacha/analyze', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          // 非 200 时先判断是否为 JSON，避免解析 HTML 错误页时报错
          const contentType = response.headers.get('content-type') || '';
          if (contentType.includes('application/json')) {
            const data = await response.json();
            throw new Error(data.detail || data.message || `识别失败 (HTTP ${response.status})`);
          } else {
            const text = await response.text();
            throw new Error(`服务器错误 (HTTP ${response.status})：${text.slice(0, 200).replace(/<[^>]+>/g, '') || '无法连接到分析服务，请确认后端已启动且本地大模型可访问'}`);
          }
        }

        const data = await response.json();

        qichachaResultData = data;
        renderQichachaResult(data);
        showToast('✅ 企查查截图识别完成');

      } catch (err) {
        resultCard.className = 'qichacha-result-card danger';
        resultCard.innerHTML = `
          <div class="qichacha-result-row">
            <span class="qichacha-result-label">❌ 错误</span>
            <span class="qichacha-result-value">${escapeHtml(err.message)}</span>
          </div>
        `;
        showToast('❌ 识别失败：' + err.message);
      } finally {
        btn.disabled = false;
        btn.textContent = '🔍 开始识别';
      }
    }

    function renderQichachaResult(data) {
      const resultCard = document.getElementById('qichachaResultCard');
      const isAbnormal = data.is_abnormal === true;

      if (isAbnormal) {
        resultCard.className = 'qichacha-result-card danger';
      } else {
        resultCard.className = 'qichacha-result-card success';
      }

      let html = '';

      if (data.company_name) {
        html += `<div class="qichacha-result-row">
          <span class="qichacha-result-label">🏢 企业</span>
          <span class="qichacha-result-value" style="font-weight:bold;">${escapeHtml(data.company_name)}</span>
        </div>`;
      }

      const statusBadgeClass = isAbnormal ? 'abnormal' : 'normal';
      html += `<div class="qichacha-result-row">
        <span class="qichacha-result-label">📊 经营状态</span>
        <span class="qichacha-result-value"><span class="qichacha-status-badge ${statusBadgeClass}">${escapeHtml(data.business_status || '未知')}</span></span>
      </div>`;

      if (data.risk_count > 0) {
        html += `<div class="qichacha-result-row">
          <span class="qichacha-result-label">⚠️ 风险数量</span>
          <span class="qichacha-result-value" style="color:${isAbnormal ? '#dc2626' : '#d97706'}; font-weight:bold;">${data.risk_count} 条</span>
        </div>`;
      }

      if (data.risk_summary) {
        html += `<div class="qichacha-result-row">
          <span class="qichacha-result-label">📝 风险摘要</span>
          <span class="qichacha-result-value">${escapeHtml(data.risk_summary)}</span>
        </div>`;
      }

      if (data.recommendation) {
        const recClass = isAbnormal ? 'danger' : 'success';
        html += `<div class="qichacha-recommendation ${recClass}">
          ${isAbnormal ? '🚫' : '✅'} ${escapeHtml(data.recommendation)}
        </div>`;
      }

      resultCard.innerHTML = html;

      // Show comparison area with original image and HTML text
      const compareArea = document.getElementById('qichachaCompareArea');
      const compareContent = document.getElementById('qichachaCompareContent');
      const originalImg = document.getElementById('qichachaOriginalImg');
      const htmlView = document.getElementById('qichachaHtmlView');

      // Get the original image preview source
      const dropZone = document.getElementById('qichachaDropZone');
      const previewImg = dropZone.querySelector('img');
      if (previewImg) {
        originalImg.src = previewImg.src;
      }

      if ((data.ocr_blocks && data.ocr_blocks.length > 0) || (data.ocr_lines && data.ocr_lines.length > 0) || data.markdown_text || data.html_content) {
        _lastOcrData = data;
        htmlView.innerHTML = renderOcrAsHtml(data);
        compareArea.style.display = 'block';
      } else {
        compareArea.style.display = 'none';
      }
    }

    // Store last OCR data for re-render on toggle
    var _lastOcrData = null;

    function toggleCompareView() {
      if (!_lastOcrData) return;

      // Get original image source
      var originalSrc = '';
      var originalImg = document.getElementById('qichachaOriginalImg');
      if (originalImg && originalImg.src) {
        originalSrc = originalImg.src;
      }

      // Open new window for comparison — wide window for full-screen feel
      var winW = Math.min(1400, screen.width - 40);
      var winH = Math.min(900, screen.height - 80);
      var left = Math.max(0, (screen.width - winW) / 2);
      var top = Math.max(0, (screen.height - winH) / 2);
      var win = window.open('', '_blank', 'width=' + winW + ',height=' + winH + ',left=' + left + ',top=' + top + ',scrollbars=yes,resizable=yes');

      var doc = win.document;
      doc.open();

      // Write HTML + CSS first (no <script> tag yet)
      doc.write('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>OCR 识别文字对比</title>');
      doc.write('<style>' +
        '* { margin:0; padding:0; box-sizing:border-box; }' +
        'body { font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Noto Sans SC,PingFang SC,Microsoft YaHei,sans-serif; background:#f9fafb; color:#1a1a2e; }' +
        '.popup-header { display:flex; align-items:center; justify-content:space-between; padding:14px 24px; background:#fff; border-bottom:1px solid #e5e7eb; position:sticky; top:0; z-index:10; }' +
        '.popup-header h2 { font-size:18px; color:#1e4a8a; }' +
        '.popup-header .close-btn { padding:6px 16px; border-radius:6px; border:1px solid #e5e7eb; background:#fff; cursor:pointer; font-size:13px; font-family:inherit; transition:all 200ms; }' +
        '.popup-header .close-btn:hover { background:#fef2f2; border-color:#ef4444; color:#ef4444; }' +
        '.popup-body { display:flex; flex-direction:column; gap:16px; padding:20px 24px; }' +
        '.popup-pane { display:flex; flex-direction:column; min-width:0; width:100%; }' +
        '.popup-pane-title { font-size:13px; font-weight:600; color:#6b7280; margin-bottom:8px; padding-bottom:6px; border-bottom:1px solid #e5e7eb; }' +
        '.popup-pane-body { flex:1; overflow-y:auto; background:#fff; border:1px solid #e5e7eb; border-radius:8px; min-height:300px; width:100%; }' +
        '.popup-pane-body img.original-img { max-width:100%; height:auto; display:block; }' +
        '.popup-pane-body iframe.ocr-iframe { width:100%; min-height:400px; border:none; background:#fff; }' +
        '.popup-pane-body .ocr-canvas { position:relative; font-family:Microsoft YaHei,PingFang SC,sans-serif; background:#fff; width:100%; }' +
        '.popup-pane-body .ocr-block { position:absolute; white-space:nowrap; color:#1a1a2e; overflow:visible; display:inline-block; }' +
        '.popup-pane-body .ocr-low-conf { background:rgba(251,191,36,0.2); border-radius:2px; padding:0 2px; }' +
        '.popup-pane-body .ocr-document { font-family:Microsoft YaHei,PingFang SC,sans-serif; padding:16px 20px; color:#1a1a2e; line-height:1.8; }' +
        '.popup-pane-body .ocr-document p { margin:0 0 4px 0; font-size:13px; white-space:pre-wrap; word-break:break-all; }' +
        '</style></head><body>');

      // Header
      doc.write('<div class="popup-header"><h2>📄 OCR 识别文字对比</h2><button class="close-btn" onclick="window.close()">关闭</button></div>');

      // Body
      doc.write('<div class="popup-body">');
      doc.write('<div class="popup-pane"><div class="popup-pane-title">AI 识别文字</div><div class="popup-pane-body" id="ocrPaneBody"></div></div>');
      doc.write('<div class="popup-pane"><div class="popup-pane-title">原图</div><div class="popup-pane-body">');
      if (originalSrc) {
        doc.write('<img class="original-img" src="' + originalSrc + '" alt="原图">');
      } else {
        doc.write('<div style="padding:24px;text-align:center;color:#9ca3af;">无原图</div>');
      }
      doc.write('</div></div>');
      doc.write('</div>');

      // Inject JS via doc.write — the _ocrData is defined as a real variable in the popup's scope
      // Using eval-like approach: define the data, then the render function, then call it
      var ocrDataJson = JSON.stringify(_lastOcrData);

      // Build the JS code as an array and join — avoids 