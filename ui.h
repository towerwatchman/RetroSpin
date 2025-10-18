#ifndef UI_H
#define UI_H

void initFramebuffer();
void cleanupFramebuffer();
void drawBackground();
void drawLogo();
void drawMenu(const std::vector<std::string>& items, int selected);
int getInput();
void drawText(int x, int y, const std::string& text, uint32_t color, int scale = 1);

extern uint32_t* fb_ptr;
extern int fb_width, fb_height, fb_bpp;

#endif