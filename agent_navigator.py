"""
Навигатор агента по сценарной сети (граф переходов в Neo4j).

Агент приходит в сценарную сеть с предзагруженными моделями этики и эмоций.
Характеристики агента — треугольные функции принадлежности Tri(a, b, c).
Узлы сети описывают события, а не характеристики агента.
"""

import random
from typing import Dict, List, Tuple
from neo4j import GraphDatabase

from emotional_model import EmotionalModel, get_peak, make_tri
from ethical_model import EthicalModel
from llm_emotion_generator import LLMEmotionGenerator
from supervisor import Supervisor

class AgentNavigator:
    """
    Навигатор агента по сценарной сети.

    Агент инициализируется ТОЛЬКО через явно переданные параметры.
    Все характеристики хранятся как Tri(a, b, c).
    """

    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.emotional_model = EmotionalModel()
        self.ethical_model = EthicalModel()
        self.path: List[Tuple] = []
        # Инициализируем генератор эмоций на основе LLM
        self.emotion_generator = LLMEmotionGenerator()
        self.supervisor = Supervisor(verbose=True)
    def close(self):
        self.driver.close()

    # ── Генерация эмоций из текста узла ──────────────────────────

    def generate_emotions_for_node(self, node_id: str) -> dict:
        """Извлекает описание узла из БД и генерирует эмоции через LLM."""
        with self.driver.session() as session:
            result = session.run(
                "MATCH (s:State {id: $node_id}) RETURN s.description AS desc",
                node_id=node_id
            )
            record = result.single()
            if record and record['desc']:
                return self.emotion_generator.generate_emotions(record['desc'])
            else:
                return {}

    # ── Получение агрегированной этической оценки действия ──────
    def regenerate_emotions_for_node(self, node_id: str):
        """
        Генерирует эмоции из описания узла и обновляет эмоциональное состояние агента.
        Используется при переходе в новый узел.
        """
        auto_emotions = self.generate_emotions_for_node(node_id)
        if not auto_emotions:
            return
        for key, value in auto_emotions.items():
            if key.startswith('emotion_'):
                name = key[len('emotion_'):]
                self.emotional_model.state[name] = make_tri(value)
    def get_action_ethics(self, action_id: str) -> float:
        """
        Возвращает агрегированную этическую оценку x1 для действия.
        Вычисляется как средневзвешенное по приоритетам норм.
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (a:Action {id: $action_id})-[r:REGULATED_BY]->(n:EthicNorm)
                RETURN n.x1 AS x1, n.priority AS priority
            """, action_id=action_id)
            records = list(result)
            if not records:
                return 0.5  # нейтральное значение по умолчанию
            total_weight = 0.0
            weighted_sum = 0.0
            for rec in records:
                x1 = rec['x1']
                p = rec['priority']
                weighted_sum += x1 * p
                total_weight += p
            return weighted_sum / total_weight if total_weight > 0 else 0.5

    # ── Инициализация агента ───────────────────────────────────────

    def init_agent(self, agent_params: dict):
        """
        Инициализировать агента с заданными характеристиками.

        Args:
            agent_params: словарь характеристик агента.
                Значения — Tri(a, b, c) в виде [a, b, c]
                Ключи: 'emotion_<n>' и 'ethic_<n>'
        """
        self.emotional_model = EmotionalModel()
        self.ethical_model = EthicalModel()

        emotion_count = 0
        ethic_count = 0

        for key, value in agent_params.items():
            if key.startswith('emotion_'):
                name = key[len('emotion_'):]
                self.emotional_model.state[name] = make_tri(value)
                emotion_count += 1
            elif key.startswith('ethic_'):
                name = key[len('ethic_'):]
                self.ethical_model.state[name] = make_tri(value)
                ethic_count += 1

        print(f"  Агент инициализирован: "
              f"{emotion_count} эмоций, {ethic_count} этических параметров")

    # ── Вычисление отклонений (для старой логики) ────────────────

    def compute_total_deviation(self, edge_props: dict) -> Tuple[float, float, float]:
        """
        Вычислить ΣΔE = ΣΔE_em + ΣΔE_eth.
        Возвращает (total, emotional_part, ethical_part).
        """
        em_dev = self.emotional_model.compute_deviation(edge_props)
        eth_dev = self.ethical_model.compute_deviation(edge_props)
        return (round(em_dev + eth_dev, 3), round(em_dev, 3), round(eth_dev, 3))

    def compute_deviation_details(self, edge_props: dict) -> List[Tuple[str, float, float, float]]:
        """
        Подробная разбивка ΣΔE по каждому условию ребра.
        Возвращает список (param_name, req_peak, agent_peak, |deviation|).
        """
        details = []
        for key, value in edge_props.items():
            if key.startswith('cond_em_') and (key.endswith('_le') or key.endswith('_ge')):
                emotion_name = key[8:-3]
                agent_peak = self.emotional_model.get_peak(emotion_name)
                req_peak = get_peak(value)
                dev = abs(req_peak - agent_peak)
                details.append((emotion_name, req_peak, agent_peak, round(dev, 3)))
            elif key.startswith('cond_eth_') and (key.endswith('_le') or key.endswith('_ge')):
                ethic_name = key[9:-3]
                agent_peak = self.ethical_model.get_peak(ethic_name)
                req_peak = get_peak(value)
                dev = abs(req_peak - agent_peak)
                details.append((ethic_name, req_peak, agent_peak, round(dev, 3)))
        return details

    # ── Применение обновлений ──────────────────────────────────────

    def apply_all_updates(self, edge_props: dict, verbose: bool = False):
        """
        Применить обновления после выбора ребра:
          1. Обновления из ребра (сдвиг Tri на delta)
          2. TSK-правила эмоциональной модели
          3. TSK-правила этической модели
        """
        self.emotional_model.apply_edge_updates(edge_props)
        self.ethical_model.apply_edge_updates(edge_props)

        em_deltas = self.emotional_model.apply_tsk_rules(verbose=verbose)
        if verbose and em_deltas:
            print(f"  Δ эмоций (TSK): {em_deltas}")

        eth_deltas = self.ethical_model.apply_tsk_rules(verbose=verbose)
        if verbose and eth_deltas:
            print(f"  Δ этики (TSK):  {eth_deltas}")

    # ── Получение состояния ────────────────────────────────────────

    def get_nonzero_state(self) -> Dict[str, str]:
        state = {}
        state.update(self.emotional_model.get_nonzero())
        state.update(self.ethical_model.get_nonzero())
        return state

    # ── Основной цикл навигации ────────────────────────────────────

    def navigate(self, start_id: str, agent_params: dict,
             verbose: bool = True, generate_emotions_from_text: bool = True) -> List[Tuple]:
        # Генерация эмоций из текста (если включено)
        if generate_emotions_from_text:
            auto_emotions = self.generate_emotions_for_node(start_id)
            merged_params = {**auto_emotions, **agent_params}
        else:
            merged_params = agent_params

        self.init_agent(merged_params)
        current = start_id
        self.path = []

        if verbose:
            print(f"\n{'='*60}")
            print(f"Начальное состояние агента (старт: узел {start_id}):")
            print(f"  Эмоции: {self.emotional_model.get_nonzero()}")
            print(f"  Этика:  {self.ethical_model.get_nonzero()}")
            print(f"{'='*60}")

        while True:
            with self.driver.session() as session:
                # Запрос к БД
                query = """
                    MATCH (current:State {id: $current})-[:OFFERS]->(a:Action)
                    MATCH (a)-[:LEADS_TO]->(next:State)
                    RETURN a, next.id AS next_id, a.id AS edge_id
                """
                result = session.run(query, current=current)
                edges = list(result)

                if verbose:
                    print(f"\n🔍 Найдено записей: {len(edges)}")

                if not edges:
                    if verbose:
                        print(f"\n  Узел {current}: нет исходящих рёбер → КОНЕЦ")
                    break

                candidates = []
                for rec in edges:
                    edge_props = dict(rec['a'])
                    edge_id = rec['edge_id']
                    next_id = rec['next_id']

                    if verbose:
                        print(f"\n  Обрабатываем действие: {edge_id}")
                        print(f"    Свойства: {edge_props}")

                    x3 = edge_props.get('intent', 0.5)
                    x1 = self.get_action_ethics(edge_id)
                    x2 = agent_params.get('perception', 0.9)
                    readiness = x1 * x2 + x3 * (1.0 - x2)

                    if verbose:
                        print(f"    x3={x3}, x1={x1:.3f}, x2={x2}")
                        print(f"    Готовность X = {readiness:.3f}")

                    candidates.append({
                        'edge_id': edge_id,
                        'next_id': next_id,
                        'readiness': readiness,
                        'props': edge_props,
                    })

                if not candidates:
                    if verbose:
                        print(f"\n  Узел {current}: нет доступных кандидатов → КОНЕЦ")
                    break

                if verbose:
                    print(f"\n=== Узел {current}: {len(candidates)} исходящих рёбер ===")
                    for c in sorted(candidates, key=lambda x: x['edge_id']):
                        print(f"  {c['edge_id']} → {c['next_id']} : Готовность X = {c['readiness']:.3f}")

                # 1. Выбираем лучшее действие
                best = max(candidates, key=lambda c: c['readiness'])
                if verbose:
                    print(f"→ ВЫБРАНО: {best['edge_id']} → {best['next_id']} (X = {best['readiness']:.3f})")

                # 2. Применяем обновления из ребра (TSK + edge updates)
                self.apply_all_updates(best['props'], verbose=verbose)

                # 3. БЛОК КОНТРОЛЛИНГА: мониторим и корректируем состояние
                supervisor_result = self.supervisor.monitor_and_correct(
                    self.emotional_model,
                    self.ethical_model,
                    best['props']
                )
                if verbose and supervisor_result['interventions']:
                    print(f"   🔧 Вмешательств: {len(supervisor_result['interventions'])}")

                # 4. Сохраняем шаг в путь
                self.path.append((current, best['edge_id'], best['next_id'], best['readiness']))

                # 5. Переходим в следующий узел
                current = best['next_id']
                # ✅ Генерация эмоций из описания нового узла
                if generate_emotions_from_text:
                    self.regenerate_emotions_for_node(current)
                    if verbose:
                        print(f"  🔄 Эмоции перегенерированы для узла {current}")
        if verbose and self.path:
            print(f"\n{'='*60}")
            print("ПРОЙДЕННЫЙ ПУТЬ:")
            for step in self.path:
                print(f"  {step[0]} --{step[1]}--> {step[2]} (X = {step[3]:.3f})")
            path_str = " → ".join([self.path[0][0]] + [s[2] for s in self.path])
            print(f"\nКраткий путь: {path_str}")
            print(f"\nФинальное состояние агента:")
            print(f"  Эмоции: {self.emotional_model.get_nonzero()}")
            print(f"  Этика:  {self.ethical_model.get_nonzero()}")
            print(f"{'='*60}")
        elif verbose and not self.path:
            print("\n⚠️ Путь пуст — агент не смог найти доступные действия")

        return self.path