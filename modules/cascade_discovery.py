import pandas as pd
import numpy as np
from collections import defaultdict, deque
import math
from typing import List, Dict, Tuple


class CascadeDiscovery:
    def __init__(self, df: pd.DataFrame, filters: List[str]):
        self.df = df
        self.filters = filters
        self.dependencies = {}
        self.cascade_order = []
        self.stats = {}
        
    def calculate_filter_stats(self) -> Dict:
        """Шаг 1: Вычисление статистик фильтров"""
        stats = {}
        
        for filter_name in self.filters:
            if filter_name in self.df.columns:
                unique_count = self.df[filter_name].nunique()
                total_count = len(self.df)
                diversity = unique_count / total_count if total_count > 0 else 0
                
                # Энтропия
                value_counts = self.df[filter_name].value_counts(normalize=True)
                entropy = -sum(p * math.log2(p) for p in value_counts if p > 0)
                
                stats[filter_name] = {
                    'unique_count': unique_count,
                    'total_count': total_count,
                    'diversity': diversity,
                    'entropy': entropy
                }
        
        self.stats = stats
        return stats
    
    def calculate_dependency(self, parent: str, child: str) -> float:
        """Шаг 2: Вычисление зависимости parent → child (оптимизированная версия)"""
        if parent not in self.df.columns or child not in self.df.columns:
            return 0.0
        
        # Количество уникальных значений child в общем
        unique_child_total = self.df[child].nunique()
        
        if unique_child_total == 0:
            return 0.0
        
        # Оптимизация: используем groupby вместо цикла
        # Группируем по parent и считаем уникальные значения child для каждой группы
        grouped = self.df.groupby(parent)[child].nunique()
        
        if len(grouped) == 0:
            return 0.0
        
        # Среднее количество уникальных child при фиксированном parent
        avg_unique_child = grouped.mean()
        
        # Коэффициент зависимости
        dependency = 1.0 - (avg_unique_child / unique_child_total)
        return max(0.0, min(1.0, dependency))
    
    def build_dependency_graph(self, threshold: float = 0.3) -> Tuple[Dict, Dict]:
        """Шаг 3: Построение графа зависимостей (оптимизированная версия)"""
        graph = defaultdict(list)  # parent -> [children]
        indegree = {f: 0 for f in self.filters if f in self.df.columns}
        
        # Оптимизация: ограничиваем количество проверяемых пар для больших наборов фильтров
        # Проверяем только основные фильтры и первые 30 фильтров для ускорения
        filters_to_check = [f for f in self.filters if f in self.df.columns]
        
        # Если фильтров слишком много, проверяем только основные и первые N
        max_filters_to_check = 30
        if len(filters_to_check) > max_filters_to_check:
            # Приоритет основным фильтрам (первые в списке)
            priority_filters = filters_to_check[:10]  # Первые 10
            other_filters = filters_to_check[10:max_filters_to_check]  # Следующие до 30
            filters_to_check = priority_filters + other_filters
        
        for i, parent in enumerate(filters_to_check):
            for j, child in enumerate(filters_to_check):
                if i != j:
                    dependency = self.calculate_dependency(parent, child)
                    if dependency > threshold:
                        graph[parent].append((child, dependency))
                        if child in indegree:
                            indegree[child] += 1
                        self.dependencies[(parent, child)] = dependency
        
        return graph, indegree
    
    def topological_sort(self, graph: Dict, indegree: Dict) -> List[str]:
        """Шаг 4: Топологическая сортировка"""
        queue = deque([filter_name for filter_name, degree in indegree.items() if degree == 0])
        cascade_order = []
        
        while queue:
            parent = queue.popleft()
            cascade_order.append(parent)
            
            for child, _ in graph.get(parent, []):
                if child in indegree:
                    indegree[child] -= 1
                    if indegree[child] == 0:
                        queue.append(child)
        
        return cascade_order
    
    def greedy_cascade(self) -> List[str]:
        """Шаг 5: Жадный алгоритм для циклических графов"""
        remaining_filters = set([f for f in self.filters if f in self.df.columns])
        cascade_order = []
        
        if not remaining_filters:
            return []
        
        # Начинаем с фильтра минимальной энтропии
        min_entropy_filter = min(
            remaining_filters, 
            key=lambda f: self.stats.get(f, {}).get('entropy', float('inf'))
        )
        cascade_order.append(min_entropy_filter)
        remaining_filters.remove(min_entropy_filter)
        
        while remaining_filters:
            current_filter = cascade_order[-1]
            best_child = None
            max_dependency = 0
            
            for child_filter in remaining_filters:
                dependency = self.calculate_dependency(current_filter, child_filter)
                if dependency > max_dependency:
                    max_dependency = dependency
                    best_child = child_filter
            
            if best_child and max_dependency > 0.2:  # Минимальный порог
                cascade_order.append(best_child)
                remaining_filters.remove(best_child)
            else:
                # Добавляем фильтр с минимальной энтропией из оставшихся
                next_filter = min(
                    remaining_filters,
                    key=lambda f: self.stats.get(f, {}).get('entropy', float('inf'))
                )
                cascade_order.append(next_filter)
                remaining_filters.remove(next_filter)
        
        return cascade_order
    
    def discover_cascade(self, threshold: float = 0.3) -> List[str]:
        """Основной метод: обнаружение каскада"""
        # Вычисляем статистику фильтров
        self.calculate_filter_stats()
        
        # Строим граф зависимостей
        graph, indegree = self.build_dependency_graph(threshold)
        
        # Выполняем топологическую сортировку
        cascade_order = self.topological_sort(graph, indegree)
        
        # Если граф циклический (не все фильтры включены)
        available_filters = [f for f in self.filters if f in self.df.columns]
        if len(cascade_order) != len(available_filters):
            # Используем жадный алгоритм
            cascade_order = self.greedy_cascade()
        
        # Добавляем фильтры, которые не попали в каскад
        remaining = [f for f in available_filters if f not in cascade_order]
        cascade_order.extend(remaining)
        
        self.cascade_order = cascade_order
        return cascade_order
    
    def get_dependencies_info(self, min_dependency: float = 0.5) -> List[Tuple[str, str, float]]:
        """Возвращает список сильных зависимостей"""
        strong_dependencies = [
            (p, c, self.dependencies[(p, c)]) 
            for (p, c) in self.dependencies 
            if self.dependencies[(p, c)] > min_dependency
        ]
        return sorted(strong_dependencies, key=lambda x: x[2], reverse=True)

