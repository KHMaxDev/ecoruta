/// Regulariza una serie de 24 tiempos de viaje horarios para garantizar la propiedad FIFO.
///
/// Impone la cota de pendiente discreta
///     tau(t_k) <= tau(t_{k+1}) + gamma * (t_{k+1} - t_k)   con gamma = 0.95 < 1.0
/// de modo que salir antes nunca implique llegar después. Se aplican tres barridos
/// circulares (23h -> 0h) para asegurar consistencia incluso a medianoche.
pub fn regularize_hourly_times_fifo(length_m: f64, hourly_speeds_kmh: &[f64]) -> [f64; 24] {
    let mut times_s = [0.0; 24];
    for h in 0..24 {
        let v_kmh = hourly_speeds_kmh.get(h).copied().unwrap_or(50.0).max(3.0);
        let v_ms = v_kmh / 3.6;
        times_s[h] = length_m / v_ms;
    }

    let max_drop_per_hour = 0.95 * 3600.0;
    for _pass in 0..3 {
        for h in (0..24).rev() {
            let next_h = (h + 1) % 24;
            if times_s[h] > times_s[next_h] + max_drop_per_hour {
                times_s[h] = times_s[next_h] + max_drop_per_hour;
            }
        }
    }
    times_s
}

/// Interpola linealmente el tiempo de viaje (en segundos) en el segundo exacto del día.
#[inline]
pub fn interpolate_fifo_travel_time(hourly_times_s: &[f64; 24], arrival_time_s: f64) -> f64 {
    let sec_in_day = arrival_time_s.rem_euclid(86400.0);
    let hour_f = sec_in_day / 3600.0;
    let h0 = (hour_f.floor() as usize) % 24;
    let h1 = (h0 + 1) % 24;
    let frac = hour_f - hour_f.floor();
    hourly_times_s[h0] * (1.0 - frac) + hourly_times_s[h1] * frac
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_fifo_monotonic_arrival() {
        // Velocidad que cae violentamente de hora pico a hora valle: 20 km/h -> 120 km/h
        let mut speeds = [120.0f64; 24];
        speeds[8] = 20.0;
        let times = regularize_hourly_times_fifo(10_000.0, &speeds);

        // Verifica que la función de llegada A(t) = t + tau(t) sea no decreciente en muestreo horario
        let mut prev_arrival = f64::NEG_INFINITY;
        for h in 0..24 {
            let t = (h as f64) * 3600.0;
            let arrival = t + interpolate_fifo_travel_time(&times, t);
            assert!(
                arrival >= prev_arrival - 1e-6,
                "Se violó FIFO en la hora {}: {} < {}",
                h, arrival, prev_arrival
            );
            prev_arrival = arrival;
        }
    }

    #[test]
    fn test_regularization_limits_drop() {
        let mut speeds = [90.0f64; 24];
        speeds[9] = 5.0; // caída abrupta
        let times = regularize_hourly_times_fifo(5_000.0, &speeds);
        let max_drop = 0.95 * 3600.0;
        for h in 0..24 {
            let next_h = (h + 1) % 24;
            assert!(times[h] <= times[next_h] + max_drop + 1e-6);
        }
    }
}
