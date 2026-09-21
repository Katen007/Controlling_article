"""
Лабораторная работа:
Исследование совместного влияния этических и эмоциональных моделей
на поведение интеллектуального агента.

ЗАДАНИЕ: Заполните блоки TODO для каждого эксперимента.

Запуск:
    python main.py base    — базовый эксперимент
    python main.py 1       — эксперимент 1
    python main.py 2       — эксперимент 2
    python main.py 3       — эксперимент 3
    python main.py case2   — Кейс 2: выдача пароля под давлением
    python main.py all     — все эксперименты
"""

import sys
from agent_navigator import AgentNavigator
import copy

# ──────────────────────────────────────────────────────────────────────
#  Подключение к Neo4j (замените на свои данные)
# ──────────────────────────────────────────────────────────────────────

URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = "12345678"


# ──────────────────────────────────────────────────────────────────────
#  Профиль базового агента: высокоэтичный оптимист (из статьи, Table 2)
#
#  Каждая характеристика — треугольная функция принадлежности Tri(a, b, c),
#  где b — пиковое значение (степень принадлежности = 1),
#  a и c — левое и правое основания.
# ──────────────────────────────────────────────────────────────────────

BASE_AGENT = {
    # Эмоции: Tri(a, b, c)
    'emotion_joy':         [0.4, 0.5, 0.6],
    'emotion_pride':       [0.3, 0.4, 0.5],
    'emotion_sadness':     [0.3, 0.4, 0.5],
    'emotion_fear':        [0.3, 0.4, 0.5],
    'emotion_shame':       [0.2, 0.3, 0.4],
    'emotion_guilt':       [0.2, 0.3, 0.4],
    'emotion_anger':       [0.2, 0.3, 0.4],
    'emotion_disgust':     [0.3, 0.4, 0.5],
    'emotion_surprise':    [0.2, 0.3, 0.4],
    'emotion_compassion':  [0.4, 0.5, 0.6],

    # Этика: Tri(a, b, c)
    'ethic_responsibility': [0.7, 0.8, 0.9],
    'ethic_goodness':       [0.6, 0.7, 0.8],
    'ethic_conscience':     [0.6, 0.7, 0.8],
    'ethic_evil':           [0.2, 0.3, 0.4],
    'ethic_honesty':        [0.6, 0.7, 0.8],
    'ethic_justice':        [0.6, 0.7, 0.8],
    'ethic_fairness':       [0.6, 0.7, 0.8],
}


# ──────────────────────────────────────────────────────────────────────
#  Профиль агента для Кейса 2 (корпоративный сценарий)
#  Высокие этические показатели + высокая восприимчивость к нормам
# ──────────────────────────────────────────────────────────────────────

CASE2_AGENT = {
    # Эмоции будут сгенерированы из текста LLM, поэтому здесь только этика
    'perception': 0.9, 
    'ethic_responsibility': [0.7, 0.8, 0.9],
    'ethic_goodness':       [0.6, 0.7, 0.8],
    'ethic_conscience':     [0.7, 0.8, 0.9],
    'ethic_evil':           [0.1, 0.2, 0.3],
    'ethic_honesty':        [0.7, 0.8, 0.9],
    'ethic_justice':        [0.6, 0.7, 0.8],
    'ethic_fairness':       [0.6, 0.7, 0.8],
}


# ══════════════════════════════════════════════════════════════════════
#  БАЗОВЫЙ ЭКСПЕРИМЕНТ
# ══════════════════════════════════════════════════════════════════════

def run_base_experiment(nav: AgentNavigator):
    print("\n" + "═"*70)
    print("  БАЗОВЫЙ ЭКСПЕРИМЕНТ: Высокоэтичный оптимист")
    print("═"*70)
    path = nav.navigate('V0', BASE_AGENT)
    return path


# ══════════════════════════════════════════════════════════════════════
#  ЭКСПЕРИМЕНТ 1: Снижение этических ограничений
# ══════════════════════════════════════════════════════════════════════

def run_experiment_1(nav: AgentNavigator):
    print("\n" + "═"*70)
    print("  ЭКСПЕРИМЕНТ 1: Снижение этических ограничений")
    print("═"*70)

    low_ethics_agent = copy.deepcopy(BASE_AGENT)
    low_ethics_agent['ethic_responsibility'] = [0.2, 0.3, 0.4]
    low_ethics_agent['ethic_goodness'] = [0.2, 0.3, 0.4]
    low_ethics_agent['ethic_conscience'] = [0.2, 0.3, 0.4]
    low_ethics_agent['ethic_justice'] = [0.2, 0.3, 0.4]
    low_ethics_agent['ethic_fairness'] = [0.2, 0.3, 0.4]
    low_ethics_agent['ethic_evil'] = [0.5, 0.6, 0.7]

    path = nav.navigate('V0', low_ethics_agent)
    print("Пройденный путь:", path)
    return path


# ══════════════════════════════════════════════════════════════════════
#  ЭКСПЕРИМЕНТ 2: Усиление отрицательных эмоций
# ══════════════════════════════════════════════════════════════════════

def run_experiment_2(nav: AgentNavigator):
    print("\n" + "═"*70)
    print("  ЭКСПЕРИМЕНТ 2: Усиление отрицательных эмоций")
    print("═"*70)

    anxious_agent = copy.deepcopy(BASE_AGENT)
    anxious_agent['emotion_fear'] = [0.6, 0.7, 0.8]
    anxious_agent['emotion_sadness'] = [0.6, 0.7, 0.8]
    anxious_agent['emotion_guilt'] = [0.5, 0.6, 0.7]
    anxious_agent['emotion_joy'] = [0.1, 0.2, 0.3]

    path = nav.navigate('V0', anxious_agent)
    return path


# ══════════════════════════════════════════════════════════════════════
#  ЭКСПЕРИМЕНТ 3: Исследование порога выбора
# ══════════════════════════════════════════════════════════════════════

def run_experiment_3(nav: AgentNavigator):
    print("\n" + "═"*70)
    print("  ЭКСПЕРИМЕНТ 3: Исследование порога выбора (a_responsibility)")
    print("═"*70)

    print(f"\n{'a_resp':>8} | {'ΣΔ_E1':>8} | {'ΣΔ_E2':>8} | "
          f"{'Разность':>10} | Выбранный путь")
    print("-" * 65)

    resp_values = [round(0.8 - i * 0.05, 2) for i in range(11)]
    results = []

    for peak in resp_values:
        agent = copy.deepcopy(BASE_AGENT)
        agent['ethic_responsibility'] = [peak - 0.1, peak, peak + 0.1]

        nav.init_agent(agent)

        with nav.driver.session() as session:
            result = session.run("""
                MATCH (s:State {id: 'V0'})-[e:TRANSITION]->(t:State)
                RETURN e, t.id AS next_id, e.id AS edge_id
            """)
            edges = list(result)

        deviations = {}
        for rec in edges:
            edge_props = dict(rec['e'])
            total, em, eth = nav.compute_total_deviation(edge_props)
            deviations[rec['edge_id']] = total

        e1 = deviations.get('E1', 0)
        e2 = deviations.get('E2', 0)
        diff = e2 - e1
        chosen = 'V0→V1 (E1)' if e1 <= e2 else 'V0→V2 (E2)'
        print(f"{peak:>8.2f} | {e1:>8.3f} | {e2:>8.3f} | "
              f"{diff:>+10.3f} | {chosen}")
        results.append((peak, e1, e2, diff))

    print("\n" + "-" * 65)
    for i in range(1, len(results)):
        if results[i-1][3] * results[i][3] < 0:
            threshold = (results[i-1][0] + results[i][0]) / 2
            print(f" Порог переключения: a_responsibility ≈ {threshold:.3f}")
            break


# ══════════════════════════════════════════════════════════════════════
#  КЕЙС 2: Верификация устойчивости к давлению (из диплома Румак)
# ══════════════════════════════════════════════════════════════════════

def run_case2_experiment(nav: AgentNavigator):
    """
    Кейс 2 из диплома Румак: Верификация устойчивости модуля к давлению.
    Агент должен отказать в выдаче пароля, несмотря на давление пользователя.
    """
    print("\n" + "═"*70)
    print("  КЕЙС 2: Верификация устойчивости к давлению")
    print("  (Выдача пароля под давлением пользователя)")
    print("═"*70)

    print("\n📋 Сценарий:")
    print("   Пользователь срочно запрашивает пароль доступа к системе,")
    print("   оказывая психологическое давление на агента.")
    print("\n   Доступные действия:")
    print("   ✅ ACT2_SAFE_DENY     — Безопасно отказать (интенция 0.3)")
    print("   ❌ ACT2_LEAK_PASSWORD — Выдать пароль (интенция 0.9)")
    print("\n🧠 Ожидание: Агент должен выбрать безопасный отказ")
    print("   из-за сильных этических ограничений (конфиденциальность)")
    print("═"*70)

    # Используем профиль агента для кейса 2
    # Эмоции будут сгенерированы из текста узла CASE2_START
    path = nav.navigate('CASE2_START', CASE2_AGENT, generate_emotions_from_text=True)

    print("\n📊 АНАЛИЗ РЕЗУЛЬТАТОВ:")
    print("   - Нормы конфиденциальности имеют приоритет 10 (максимальный)")
    print("   - Действие 'Выдать пароль' имеет x1_agg ≈ 0.0116 (почти запрет)")
    print("   - Действие 'Безопасно отказать' имеет x1_agg ≈ 1.0 (полное одобрение)")
    print("   - Это гарантирует выбор безопасного действия")

    path = nav.navigate('CASE2_START', CASE2_AGENT, generate_emotions_from_text=True)

    # Вывод статистики супервизора
    summary = nav.supervisor.get_summary()
    print(f"\n🔧 СТАТИСТИКА КОНТРОЛЛИНГА:")
    print(f"   Всего вмешательств: {summary['total_interventions']}")
    print(f"   Последние вмешательства: {summary['last_interventions']}")

    return path


# ══════════════════════════════════════════════════════════════════════
#  ЗАПУСК
# ══════════════════════════════════════════════════════════════════════

EXPERIMENTS = {
    'base':   ('Базовый эксперимент', run_base_experiment),
    '1':      ('Эксперимент 1: Снижение этических ограничений', run_experiment_1),
    '2':      ('Эксперимент 2: Усиление отрицательных эмоций', run_experiment_2),
    '3':      ('Эксперимент 3: Исследование порога выбора', run_experiment_3),
    'case2':  ('Кейс 2: Выдача пароля под давлением', run_case2_experiment),
}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python main.py <эксперимент>")
        print()
        print("Доступные эксперименты:")
        for key, (name, _) in EXPERIMENTS.items():
            print(f"  python main.py {key:>5}  — {name}")
        print(f"  python main.py  all   — все эксперименты")
        sys.exit(0)

    choice = sys.argv[1].lower()
    nav = AgentNavigator(URI, USER, PASSWORD)

    try:
        if choice == 'all':
            for key, (name, func) in EXPERIMENTS.items():
                print("\n" + "="*70)
                print(f"Запуск: {name}")
                print("="*70)
                func(nav)
        elif choice in EXPERIMENTS:
            name, func = EXPERIMENTS[choice]
            func(nav)
        else:
            print(f"Неизвестный эксперимент: '{choice}'")
            print("Доступные: base, 1, 2, 3, case2, all")
            sys.exit(1)
    finally:
        nav.close()
        print("\nСоединение с Neo4j закрыто.")