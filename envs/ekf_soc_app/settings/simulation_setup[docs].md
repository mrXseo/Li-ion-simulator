### internal code annotations:
*	 name : **engine**

	 typing : **<class 'core.simulation_base.simulation_engine.SimulationEngine'>**


*	 name : **records_path**

	 typing : **typing.Optional[pathlib.Path]**

	 default : **None**


*	 name : **current_mode**

	 typing : **<class 'str'>**

	 default : **constant**


*	 name : **current_value**

	 typing : **<class 'float'>**

	 default : **1.0**


*	 name : **current_profile**

	 typing : **typing.Optional[list]**

	 default : **None**


*	 name : **current_profile_scale**

	 typing : **typing.Optional[int]**

	 default : **None**


*	 name : **temperature_value**

	 typing : **<class 'float'>**

	 default : **25.0**


*	 name : **battery_params**

	 typing : **typing.Optional[dict]**

	 default : **None**


*	 name : **noise_sigma**

	 typing : **<class 'float'>**

	 default : **0.01**


*	 name : **noise_bias**

	 typing : **<class 'float'>**

	 default : **0.0**


*	 name : **ekf_params**

	 typing : **typing.Optional[dict]**

	 default : **None**


### internal code doc:

        Args:
            engine: движок симуляции.
            current_mode: 'constant' или 'cyclic'.
            current_value: значение тока для режима 'constant' (А).
            current_profile: список значений тока для режима 'cyclic'.
            temperature_value: значение температуры (°C).
            battery_params: словарь параметров для BatteryThevenin1RC.
            noise_sigma: СКО шума измерения напряжения.
            noise_bias: смещение шума.
            ekf_params: словарь параметров для EKFSOCEstimator (Q, R, P0, x0).
        