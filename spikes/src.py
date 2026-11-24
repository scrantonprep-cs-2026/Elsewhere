from pathlib import Path
import pygame

# Settings
windowWidth = 1280
windowHeight = 720
viewWidth = 960      # how much of the level you see at once (it gets stretched to fill the window)
viewHeight = 540

groundY = 702        # y of the grass you walk on
playerWidth = 42
playerHeight = 74
startX = 90
startY = groundY - playerHeight

runSpeed = 300
jumpSpeed = 850
gravity = 1550

spriteSize = 110
frameCount = 40      # frames in the sprite sheet
animationFramesPerSecond = 24
jumpingFrameNumber = 21

""" Things you can stand on. Each one is a line through a list of (x, y) points,
so a branch can slope up or down and you can walk along it.
You can jump up through them from below and land on top.
Press C in the game to see these lines.
"""
platforms = [
    # left tree
    [(0, 165), (135, 165)],                                    # top-left branch
    [(140, 281), (200, 276), (260, 267), (300, 245),
     (330, 215), (350, 200), (415, 194)],                       # branch angling up off the trunk
    [(370, 352), (450, 355), (670, 357)],                       # long middle branch
    [(195, 510), (440, 512)],                                   # low branch
    [(615, 340), (650, 315), (685, 293), (720, 277),
     (830, 276), (850, 268), (1015, 268)],                      # high branch toward the middle
    # hill with the house
    [(860, 540), (1110, 540)],                                  # mossy ledge by the waterfall
    [(1000, 487), (1460, 487)],                                 # top of the hill
    # right tree
    [(1350, 285), (1400, 278), (1450, 272), (1500, 265),
     (1530, 258), (1550, 252), (1635, 252)],                    # upper-left branch
    [(1612, 387), (1650, 373), (1700, 366), (1750, 363),
     (1800, 359), (1850, 352), (1968, 350)],                    # long lower branch
    [(1785, 177), (1845, 177), (1910, 172), (1983, 168)],       # top-right branch
]
maxStepUpHeight = 12   # how many pixels you can step up while walking along a slope

# Each enemy walks back and forth on the ground between these two x values.
enemyPaths = [(355, 475), (790, 930), (1180, 1390), (1710, 1960)]
enemyRadius = 22
enemySpeed = 90
shotSpeed = 780
shotRadius = 7


def platformHeight(platformPoints, positionX):
    """Return the y of the platform's top at this x, or None if x isn't over it."""
    for pointNumber in range(len(platformPoints) - 1):
        segmentStartX, segmentStartY = platformPoints[pointNumber]
        segmentEndX, segmentEndY = platformPoints[pointNumber + 1]
        if segmentStartX <= positionX <= segmentEndX:
            distanceAlongSegment = (positionX - segmentStartX) / (segmentEndX - segmentStartX)
            return segmentStartY + (segmentEndY - segmentStartY) * distanceAlongSegment
    return None


def makeEnemies():
    enemies = []
    for pathLeftX, pathRightX in enemyPaths:
        enemies.append({
            "x": pathLeftX,
            "pathLeftX": pathLeftX,
            "pathRightX": pathRightX,
            "direction": 1,
            "alive": True,
        })
    return enemies


# Setup
pygame.init()
screen = pygame.display.set_mode((windowWidth, windowHeight))
pygame.display.set_caption("Elsewhere")
cameraView = pygame.Surface((viewWidth, viewHeight))
clock = pygame.time.Clock()
smallFont = pygame.font.Font(None, 30)
largeFont = pygame.font.Font(None, 40)

gameFolder = Path(__file__).parent
background = pygame.image.load(gameFolder / "elsewhere_demo_background.png").convert()
spriteSheet = pygame.image.load(gameFolder / "opieidleearhuge_spritesheet.png").convert_alpha()
levelWidth = background.get_width()
levelHeight = background.get_height()

# The gate you have to touch to win
portalHitbox = pygame.Rect(0, 0, 62, 106)
portalHitbox.midbottom = (levelWidth - 105, groundY - 4)

# Cut the sprite sheet into separate frames
frameWidth = spriteSheet.get_width() // frameCount
animationFrames = []
for frameNumber in range(frameCount):
    frame = spriteSheet.subsurface((frameNumber * frameWidth, 0, frameWidth, spriteSheet.get_height()))
    animationFrames.append(pygame.transform.scale(frame, (spriteSize, spriteSize)))

# Player state
playerX = startX
playerY = startY
playerVelocityY = 0
playerOnGround = True
playerFacingRight = True
animationTime = 0

enemies = makeEnemies()
shots = []
playerWon = False
showCollisionLines = False

# Gameplay
running = True
while running:
    secondsSinceLastFrame = min(clock.tick(60) / 1000, 1 / 30)

    # Key presses
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            jumpPressed = event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w)
            shootPressed = event.key in (pygame.K_j, pygame.K_x)
            if jumpPressed and playerOnGround and not playerWon:
                playerVelocityY = -jumpSpeed
            elif shootPressed and not playerWon:
                shots.append({
                    "x": playerX + playerWidth / 2,
                    "y": playerY + playerHeight / 2,
                    "direction": 1 if playerFacingRight else -1,
                })
            elif event.key == pygame.K_c:
                showCollisionLines = not showCollisionLines
            elif event.key == pygame.K_r and playerWon:
                playerX = startX
                playerY = startY
                playerVelocityY = 0
                enemies = makeEnemies()
                shots = []
                playerWon = False

    pressedKeys = pygame.key.get_pressed()
    moveDirection = 0
    if pressedKeys[pygame.K_LEFT] or pressedKeys[pygame.K_a]:
        moveDirection -= 1
    if pressedKeys[pygame.K_RIGHT] or pressedKeys[pygame.K_d]:
        moveDirection += 1
    if playerWon:
        moveDirection = 0
    if moveDirection != 0:
        playerFacingRight = moveDirection > 0

    # Move left and right
    playerX += moveDirection * runSpeed * secondsSinceLastFrame
    playerX = max(0, min(levelWidth - playerWidth, playerX))

    # Fall and jump
    previousFeetY = playerY + playerHeight
    wasOnGround = playerOnGround
    playerVelocityY += gravity * secondsSinceLastFrame
    playerY += playerVelocityY * secondsSinceLastFrame
    playerOnGround = False

    # Land on a platform when falling onto it.
    # While standing on one, also stick to it when walking up or down its slope.
    if playerVelocityY >= 0:
        feetY = playerY + playerHeight
        playerMiddleX = playerX + playerWidth / 2
        highestPlatformTop = None
        for platformPoints in platforms:
            platformTop = platformHeight(platformPoints, playerMiddleX)
            if platformTop is None or previousFeetY > platformTop + maxStepUpHeight:
                continue
            walkingOnPlatform = wasOnGround and platformTop - feetY <= maxStepUpHeight
            if feetY >= platformTop or walkingOnPlatform:
                if highestPlatformTop is None or platformTop < highestPlatformTop:
                    highestPlatformTop = platformTop
        if highestPlatformTop is not None:
            playerY = highestPlatformTop - playerHeight
            playerVelocityY = 0
            playerOnGround = True

    if playerY + playerHeight >= groundY:
        playerY = groundY - playerHeight
        playerVelocityY = 0
        playerOnGround = True

    playerHitbox = pygame.Rect(round(playerX), round(playerY), playerWidth, playerHeight)

    # Enemies walk back and forth
    for enemy in enemies:
        enemy["x"] += enemy["direction"] * enemySpeed * secondsSinceLastFrame
        if enemy["x"] < enemy["pathLeftX"] or enemy["x"] > enemy["pathRightX"]:
            enemy["direction"] *= -1

    # Shots fly and hit enemies
    for shot in shots[:]:
        shot["x"] += shot["direction"] * shotSpeed * secondsSinceLastFrame
        if shot["x"] < 0 or shot["x"] > levelWidth:
            shots.remove(shot)
            continue
        for enemy in enemies:
            enemyCenterY = groundY - enemyRadius
            touchingDistance = enemyRadius + shotRadius
            shotTouchesEnemy = (abs(shot["x"] - enemy["x"]) < touchingDistance
                                  and abs(shot["y"] - enemyCenterY) < touchingDistance)
            if enemy["alive"] and shotTouchesEnemy:
                enemy["alive"] = False
                shots.remove(shot)
                break

    # Touching an enemy sends you back to the start
    for enemy in enemies:
        enemyHitbox = pygame.Rect(enemy["x"] - enemyRadius, groundY - enemyRadius * 2,
                                   enemyRadius * 2, enemyRadius * 2)
        if enemy["alive"] and playerHitbox.colliderect(enemyHitbox):
            playerX = startX
            playerY = startY
            playerVelocityY = 0

    if playerHitbox.colliderect(portalHitbox):
        playerWon = True

    # Camera follows the player
    cameraX = max(0, min(levelWidth - viewWidth, playerHitbox.centerx - viewWidth // 2))
    cameraY = max(0, min(levelHeight - viewHeight, playerHitbox.centery - viewHeight // 2))

    # Drawing
    cameraView.blit(background, (-cameraX, -cameraY))

    if showCollisionLines:
        lineColor = (255, 230, 0)
        for platformPoints in platforms:
            screenPoints = [(pointX - cameraX, pointY - cameraY) for pointX, pointY in platformPoints]
            pygame.draw.lines(cameraView, lineColor, False, screenPoints, 3)
        pygame.draw.line(cameraView, lineColor, (0, groundY - cameraY), (viewWidth, groundY - cameraY), 3)

    portalOnScreen = portalHitbox.move(-cameraX, -cameraY)
    pygame.draw.ellipse(cameraView, (38, 31, 57), portalOnScreen)
    pygame.draw.ellipse(cameraView, (155, 127, 204), portalOnScreen.inflate(-12, -10), 5)

    for enemy in enemies:
        if enemy["alive"]:
            enemyCenter = (enemy["x"] - cameraX, groundY - enemyRadius - cameraY)
            pygame.draw.circle(cameraView, (204, 74, 108), enemyCenter, enemyRadius)

    for shot in shots:
        shotCenter = (shot["x"] - cameraX, shot["y"] - cameraY)
        pygame.draw.circle(cameraView, (244, 211, 135), shotCenter, shotRadius)

    # Player sprite
    animationTime += secondsSinceLastFrame
    currentFrameNumber = int(animationTime * animationFramesPerSecond) % frameCount
    if not playerOnGround:
        currentFrameNumber = jumpingFrameNumber
    playerSprite = animationFrames[currentFrameNumber]
    if not playerFacingRight:
        playerSprite = pygame.transform.flip(playerSprite, True, False)
    spritePosition = playerSprite.get_rect(
        midbottom=(playerHitbox.centerx - cameraX, playerHitbox.bottom + 3 - cameraY)
    )
    cameraView.blit(playerSprite, spritePosition)

    # Stretch the view to fill the window, then draw text on top
    pygame.transform.scale(cameraView, (windowWidth, windowHeight), screen)
    controlsText = smallFont.render("Move: A/D   Jump: Space   Shoot: J   Show lines: C", True, (235, 225, 205))
    screen.blit(controlsText, (20, 20))

    if playerWon:
        winText = largeFont.render("You made it!  Press R to play again", True, (248, 229, 198))
        screen.blit(winText, winText.get_rect(center=(windowWidth // 2, 120)))

    pygame.display.flip()

pygame.quit()
