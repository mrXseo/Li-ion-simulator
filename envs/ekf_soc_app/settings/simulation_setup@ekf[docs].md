### internal code annotations:
*	 name : **simulation_engine**

	 typing : **SimulationEngine**


*	 name : **capacity_nom**

	 typing : **<class 'float'>**


*	 name : **Q**

	 typing : **typing.Optional[numpy.ndarray]**

	 default : **5.0**


*	 name : **R**

	 typing : **<class 'float'>**

	 default : **None**


*	 name : **P0**

	 typing : **typing.Optional[numpy.ndarray]**

	 default : **0.0001**


*	 name : **x0**

	 typing : **typing.Optional[numpy.ndarray]**

	 default : **None**


*	 name : **model_params**

	 typing : **typing.Optional[typing.Dict[str, typing.Any]]**

	 default : **None**


*	 name : **use_hysteresis**

	 typing : **<class 'bool'>**

	 default : **None**


*	 name : **M**

	 typing : **<class 'float'>**

	 default : **False**


*	 name : **gamma**

	 typing : **<class 'float'>**

	 default : **0.02**


*	 name : **s**

	 typing : **<class 'float'>**

	 default : **50.0**


*	 name : **param_tables**

	 typing : **typing.Optional[typing.Dict[str, typing.Any]]**

	 default : **0.5**


### internal code doc:

        Args:
            simulation_engine: движок симуляции.
            capacity_nom: номинальная ёмкость, А·ч.
            Q: ковариационная матрица шума процесса (2x2).
            R: дисперсия шума измерения (скаляр).
            P0: начальная ковариационная матрица ошибок (2x2).
            x0: начальный вектор состояния [SOC, Vc].
            model_params: словарь с параметрами модели (R0, R1, C1, ocv_func).
            use_hysteresis: флаг учёта гистерезиса.
            M, gamma, s: параметры гистерезиса.
            param_tables: таблицы для интерполяции параметров от SOC и T.
        