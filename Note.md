import pygame

pygame.init()
screen = pygame.display.set_mode((800, 600))
x, y = 100, 200                # ตัวละครเริ่มตรงไหน
speed = 3

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()
    if keys[pygame.K_RIGHT]: x += speed
    if keys[pygame.K_LEFT]: x -= speed
    if keys[pygame.K_UP]: y -= speed
    if keys[pygame.K_DOWN]: y += speed

    screen.fill((255,255,255))
    pygame.draw.circle(screen, (0,0,255), (x,y), 30)
    pygame.display.flip()
pygame.quit()
