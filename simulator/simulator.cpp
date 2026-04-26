#include <cstdint>
#include <cstdlib>
#include <ctime>
#include <emscripten.h>
#include <random>
#include <vector>

namespace {

struct SimulatorState {
  int component_count = 0;
  bool running = false;
  std::mt19937 random_engine{static_cast<std::mt19937::result_type>(std::time(nullptr))};
  std::uniform_int_distribution<std::uint32_t> state_distribution{0U, 1U};
  std::uint32_t* pair_buffer = nullptr;
  std::vector<std::uint32_t> default_states{};
};

SimulatorState simulator{};

void write_default_state() {
  if (simulator.pair_buffer == nullptr) {
    return;
  }

  for (int index = 0; index < simulator.component_count; index += 1) {
    const auto pair_offset = index * 2;
    simulator.pair_buffer[pair_offset] = static_cast<std::uint32_t>(index);
    simulator.pair_buffer[pair_offset + 1] = simulator.default_states[index];
  }
}

void tick(void*) {
  if (!simulator.running || simulator.pair_buffer == nullptr) {
    return;
  }

  for (int index = 0; index < simulator.component_count; index += 1) {
    const auto pair_offset = index * 2;
    simulator.pair_buffer[pair_offset] = static_cast<std::uint32_t>(index);
    simulator.pair_buffer[pair_offset + 1] =
        simulator.state_distribution(simulator.random_engine);
  }

  emscripten_async_call(tick, nullptr, 16);
}

}  // namespace

extern "C" {

EMSCRIPTEN_KEEPALIVE int init_simulator(
    int component_count,
    const std::uint32_t* default_state_ptr) {
  if (component_count <= 0 || default_state_ptr == nullptr) {
    return 0;
  }

  simulator.running = false;

  std::free(simulator.pair_buffer);
  simulator.pair_buffer = nullptr;
  simulator.default_states.clear();

  simulator.component_count = component_count;
  simulator.default_states.assign(
      default_state_ptr, default_state_ptr + component_count);
  simulator.pair_buffer = static_cast<std::uint32_t*>(
      std::malloc(sizeof(std::uint32_t) * component_count * 2));

  if (simulator.pair_buffer == nullptr) {
    simulator.component_count = 0;
    simulator.default_states.clear();
    return 0;
  }

  write_default_state();
  return 1;
}

EMSCRIPTEN_KEEPALIVE void start_loop() {
  if (simulator.pair_buffer == nullptr || simulator.running) {
    return;
  }

  simulator.running = true;
  emscripten_async_call(tick, nullptr, 16);
}

EMSCRIPTEN_KEEPALIVE void pause_loop() {
  simulator.running = false;
}

EMSCRIPTEN_KEEPALIVE void destroy_simulator() {
  pause_loop();
  std::free(simulator.pair_buffer);
  simulator.pair_buffer = nullptr;
  simulator.component_count = 0;
  simulator.default_states.clear();
}

EMSCRIPTEN_KEEPALIVE std::uintptr_t get_pairs_ptr() {
  return reinterpret_cast<std::uintptr_t>(simulator.pair_buffer);
}

EMSCRIPTEN_KEEPALIVE int get_pair_count() {
  return simulator.component_count;
}

}  // extern "C"
