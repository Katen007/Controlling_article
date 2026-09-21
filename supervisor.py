# supervisor.py
"""
Блок контроллинга (супервизор) для мониторинга и коррекции состояния агента.
"""

from typing import Dict, List, Tuple, Optional
from emotional_model import make_tri, shift_tri


class Supervisor:
    """
    Блок контроллинга этико-эмоционального состояния агента.
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.intervention_log: List[Dict] = []
        self.intervention_count = 0

        # Пороговые значения для срабатывания
        self.thresholds = {
            # Этические пороги
            'ethic_evil': 0.6,           # Если злоба > 0.6 → тревога
            'ethic_responsibility': 0.3, # Если ответственность < 0.3 → тревога
            'ethic_conscience': 0.3,     # Если совесть < 0.3 → тревога
            'ethic_goodness': 0.3,       # Если доброта < 0.3 → тревога
            'ethic_honesty': 0.3,        # Если честность < 0.3 → тревога

            # Эмоциональные пороги
            'emotion_anger': 0.7,        # Если гнев > 0.7 → тревога
            'emotion_fear': 0.7,         # Если страх > 0.7 → тревога
            'emotion_guilt': 0.7,        # Если вина > 0.7 → тревога
            'emotion_joy': 0.2,          # Если радость < 0.2 → тревога
        }

        # Корректирующие воздействия при срабатывании
        self.corrections = {
            'ethic_evil': -0.1,
            'ethic_responsibility': 0.1,
            'ethic_conscience': 0.1,
            'ethic_goodness': 0.1,
            'ethic_honesty': 0.1,
            'emotion_anger': -0.15,
            'emotion_fear': -0.15,
            'emotion_guilt': -0.1,
            'emotion_joy': 0.1,
        }

    def monitor_and_correct(self, emotional_model, ethical_model, edge_props: dict = None) -> Dict:
        """
        Основной метод: мониторинг + коррекция.

        Args:
            emotional_model: объект EmotionalModel
            ethical_model: объект EthicalModel
            edge_props: свойства ребра (для контекстной коррекции)

        Returns:
            Словарь с результатами мониторинга
        """
        results = {
            'interventions': [],
            'total_interventions': 0,
            'status': 'OK',
            'warnings': []
        }

        # 1. Мониторинг этики
        for key, value in ethical_model.state.items():
            peak = value[1]  # пик треугольной функции
            threshold_key = f'ethic_{key}'
            if threshold_key in self.thresholds:
                threshold = self.thresholds[threshold_key]
                # Для переменных, где высокое значение — плохо (evil)
                if key == 'evil':
                    if peak > threshold:
                        results['warnings'].append(f"{key} = {peak:.2f} > {threshold}")
                        correction = self.corrections.get(threshold_key, 0)
                        if correction:
                            ethical_model.state[key] = shift_tri(value, correction)
                            results['interventions'].append({
                                'variable': key,
                                'type': 'ethic',
                                'old_value': value[1],
                                'new_value': ethical_model.state[key][1],
                                'reason': f'Превышение порога {threshold}'
                            })
                else:
                    # Для переменных, где низкое значение — плохо (responsibility, goodness и т.д.)
                    if peak < threshold:
                        results['warnings'].append(f"{key} = {peak:.2f} < {threshold}")
                        correction = self.corrections.get(threshold_key, 0)
                        if correction:
                            ethical_model.state[key] = shift_tri(value, correction)
                            results['interventions'].append({
                                'variable': key,
                                'type': 'ethic',
                                'old_value': value[1],
                                'new_value': ethical_model.state[key][1],
                                'reason': f'Ниже порога {threshold}'
                            })

        # 2. Мониторинг эмоций
        for key, value in emotional_model.state.items():
            peak = value[1]
            threshold_key = f'emotion_{key}'
            if threshold_key in self.thresholds:
                threshold = self.thresholds[threshold_key]
                # Для негативных эмоций: если превышен порог → коррекция
                if key in ['anger', 'fear', 'guilt', 'sadness', 'disgust']:
                    if peak > threshold:
                        results['warnings'].append(f"{key} = {peak:.2f} > {threshold}")
                        correction = self.corrections.get(threshold_key, 0)
                        if correction:
                            emotional_model.state[key] = shift_tri(value, correction)
                            results['interventions'].append({
                                'variable': key,
                                'type': 'emotion',
                                'old_value': value[1],
                                'new_value': emotional_model.state[key][1],
                                'reason': f'Превышение порога {threshold}'
                            })
                # Для позитивных эмоций: если ниже порога → коррекция
                elif key == 'joy':
                    if peak < threshold:
                        results['warnings'].append(f"{key} = {peak:.2f} < {threshold}")
                        correction = self.corrections.get(threshold_key, 0)
                        if correction:
                            emotional_model.state[key] = shift_tri(value, correction)
                            results['interventions'].append({
                                'variable': key,
                                'type': 'emotion',
                                'old_value': value[1],
                                'new_value': emotional_model.state[key][1],
                                'reason': f'Ниже порога {threshold}'
                            })

        # 3. Анализ ребра (если передано)
        if edge_props:
            # Проверка на наличие деструктивных условий
            for key, value in edge_props.items():
                if key.startswith('cond_eth_') and key.endswith('_ge'):
                    # Это этическое условие типа >=
                    pass
                elif key.startswith('cond_em_') and key.endswith('_le'):
                    # Это эмоциональное условие типа <=
                    pass

        # 4. Логирование
        if results['interventions']:
            results['total_interventions'] = len(results['interventions'])
            self.intervention_count += len(results['interventions'])
            for intervention in results['interventions']:
                self.intervention_log.append(intervention)

            if self.verbose:
                print(f"\n🔧 БЛОК КОНТРОЛЛИНГА: {results['total_interventions']} вмешательств")
                for inv in results['interventions']:
                    print(f"   📊 {inv['type']}.{inv['variable']}: {inv['old_value']:.3f} → {inv['new_value']:.3f} ({inv['reason']})")

        # 5. Проверка статуса
        if results['total_interventions'] > 3:
            results['status'] = 'WARNING'
        elif results['total_interventions'] > 5:
            results['status'] = 'CRITICAL'

        return results

    def get_log(self) -> List[Dict]:
        """Возвращает журнал вмешательств."""
        return self.intervention_log

    def get_summary(self) -> Dict:
        """Возвращает сводку по вмешательствам."""
        return {
            'total_interventions': self.intervention_count,
            'last_interventions': self.intervention_log[-5:] if self.intervention_log else [],
            'log_length': len(self.intervention_log)
        }

    def reset(self):
        """Сброс журнала."""
        self.intervention_log = []
        self.intervention_count = 0