#include <stdio.h>

#include "hardware/dma.h"
#include "hardware/irq.h"
#include "output.pio.h"
#include "pico/stdlib.h"
#include "tusb.h"

#define OUTPUT_PIN_BASE 1

#define MAIN_DMA_CHANNEL 0
#define CONTROL_DMA_CHANNEL 1

//uint8_t data[200000] __attribute__((aligned(4)));
#include "data.c"
uint8_t *data_ptr __attribute__((aligned(4))) = data;

void dma_init(PIO pio, uint sm, int size) {
    dma_claim_mask((1 << MAIN_DMA_CHANNEL) | (1 << CONTROL_DMA_CHANNEL));

    // stop previous DMA transfer (from https://forums.raspberrypi.com/viewtopic.php?t=337439)
    // TODO: doesn't work
    dma_hw->abort = (1 << MAIN_DMA_CHANNEL) | (1 << CONTROL_DMA_CHANNEL);
    while (dma_hw->abort) tight_loop_contents();
    while (dma_hw->ch[MAIN_DMA_CHANNEL].ctrl_trig & DMA_CH0_CTRL_TRIG_BUSY_BITS) tight_loop_contents();
    while (dma_hw->ch[CONTROL_DMA_CHANNEL].ctrl_trig & DMA_CH0_CTRL_TRIG_BUSY_BITS) tight_loop_contents();
    hw_clear_bits(&dma_hw->ch[0].al1_ctrl, DMA_CH0_CTRL_TRIG_EN_BITS);
    hw_clear_bits(&dma_hw->ch[1].al1_ctrl, DMA_CH0_CTRL_TRIG_EN_BITS);

    // main DMA channel: transfer buffer to PIO program
    dma_channel_config channel_config =
        dma_channel_get_default_config(MAIN_DMA_CHANNEL);
    channel_config_set_dreq(&channel_config, pio_get_dreq(pio, sm, true));
    channel_config_set_irq_quiet(&channel_config, true);
    channel_config_set_transfer_data_size(&channel_config, DMA_SIZE_8);
    channel_config_set_read_increment(&channel_config, true);
    channel_config_set_write_increment(&channel_config, false);
    channel_config_set_chain_to(&channel_config, CONTROL_DMA_CHANNEL);
    dma_channel_configure(MAIN_DMA_CHANNEL, &channel_config, &pio->txf[sm],
                          data, size, true);

    // using a second DMA channel with the same buffer doesn't work
    // workaround: use the second DMA channel to reset the read address of the
    // first DMA channel
    // idea from here: https://vanhunteradams.com/Pico/DAC/DMA_DAC.html
    dma_channel_config channel_config2 =
        dma_channel_get_default_config(CONTROL_DMA_CHANNEL);
    channel_config_set_transfer_data_size(&channel_config2, DMA_SIZE_32);
    channel_config_set_read_increment(&channel_config2, false);
    channel_config_set_write_increment(&channel_config2, false);
    channel_config_set_chain_to(&channel_config2, MAIN_DMA_CHANNEL);
    dma_channel_configure(CONTROL_DMA_CHANNEL, &channel_config2,
                          &dma_hw->ch[0].read_addr, &data_ptr, 1, false);
}

uint8_t parse_hex(int c) {
    if (c >= '0' && c <= '9') return c - '0';
    return c - 'a' + 10;
}

int main() {
    // load PIO program
    PIO pio = pio0;
    uint offset = pio_add_program(pio, &output_program);
    uint sm = pio_claim_unused_sm(pio, true);
    output_program_init(pio, sm, offset, OUTPUT_PIN_BASE, 8, 5 * 1000 * 1000);

    // init DMA with sawtooth test pattern
    /*
    for (int i = 0; i < 64; i++) {
        data[i] = i;
    }
    dma_init(pio, sm, 64);
    */
    dma_init(pio, sm, sizeof(data));

    // init stdio
    stdio_init_all();
    while (!tud_cdc_connected()) {
        sleep_ms(100);
    }

    int reading = 0;
    int low = 0;
    uint8_t b = 0;
    int index = 0;
    while (true) {
        int c;
        while ((c = getchar()) < 0) tight_loop_contents();
        if (reading) {
            if (c == '.') {
                printf("data read: %i bytes\n", index);
                fflush(stdout);
                dma_init(pio, sm, index);
                reading = 0;
            } else {
                if (low) {
                    b |= parse_hex(c);
                    low = 0;
                    if (index < sizeof(data)) {
                        data[index++] = b;
                    }
                } else {
                    b = parse_hex(c) << 4;
                    low = 1;
                }
            }
        } else {
            if (c == 's') {
                reading = 1;
                low = 0;
                index = 0;
            }
        }
    }
}
