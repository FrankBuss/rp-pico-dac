cmake_minimum_required(VERSION 3.13)

include($ENV{PICO_SDK_PATH}/external/pico_sdk_import.cmake)

project(output_pio C CXX ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

# init SDK
pico_sdk_init()

# define executable output and C source files
add_executable(${PROJECT_NAME} main.c)

# add additional include directory (was not set by pico_sdk_init)
target_include_directories(${PROJECT_NAME} PUBLIC
  $ENV{PICO_SDK_PATH}/src/rp2_common/hardware_pio/include
)

# add PIO file
pico_generate_pio_header(${PROJECT_NAME} ${CMAKE_CURRENT_LIST_DIR}/output.pio)

# add SDK libraries
target_link_libraries(${PROJECT_NAME} pico_stdlib hardware_dma hardware_gpio hardware_pio)

# enable USB output, disable uart output
pico_enable_stdio_usb(${PROJECT_NAME} 1)
pico_enable_stdio_uart(${PROJECT_NAME} 0)

# create uf2 file
pico_add_extra_outputs(${PROJECT_NAME})
