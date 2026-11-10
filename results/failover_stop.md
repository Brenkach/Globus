### Відмова вузла (stop app2)

| Секунда | Подія | Обслужили (app-1 / app-2 / app-3) | Помилки клієнта | Стан пулу в HAProxy |
|---|---|---|---|---|
| 0 |  | 254 / 253 / 253 | 0 | app1=UP app2=UP app3=UP |
| 1 |  | 252 / 253 / 253 | 0 | app1=UP app2=UP app3=UP |
| 2 |  | 374 / 373 / 373 | 0 | app1=UP app2=UP app3=UP |
| 3 |  | 269 / 269 / 270 | 0 | app1=UP app2=UP app3=UP |
| 4 |  | 247 / 249 / 248 | 0 | app1=UP app2=UP app3=UP |
| 5 | stop app2 | 436 / 76 / 434 | 0 | app1=UP app2=DOWN app3=UP |
| 6 |  | 446 / 0 / 446 | 0 | app1=UP app2=DOWN app3=UP |
| 7 |  | 385 / 0 / 385 | 0 | app1=UP app2=DOWN app3=UP |
| 8 |  | 482 / 0 / 482 | 0 | app1=UP app2=DOWN app3=UP |
| 9 |  | 467 / 0 / 468 | 0 | app1=UP app2=DOWN app3=UP |
| 10 |  | 437 / 0 / 436 | 0 | app1=UP app2=MAINT app3=UP |
| 11 |  | 496 / 0 / 496 | 0 | app1=UP app2=MAINT app3=UP |
| 12 |  | 380 / 0 / 380 | 0 | app1=UP app2=MAINT app3=UP |
| 13 |  | 470 / 0 / 470 | 0 | app1=UP app2=MAINT app3=UP |
| 14 |  | 509 / 0 / 509 | 0 | app1=UP app2=MAINT app3=UP |
| 15 | start app2 | 325 / 0 / 325 | 0 | app1=UP app2=MAINT app3=UP |
| 16 |  | 509 / 0 / 509 | 0 | app1=UP app2=MAINT app3=UP |
| 17 |  | 457 / 0 / 457 | 0 | app1=UP app2=DOWN app3=UP |
| 18 |  | 388 / 0 / 388 | 0 | app1=UP app2=DOWN app3=UP |
| 19 |  | 570 / 0 / 570 | 0 | app1=UP app2=DOWN app3=UP |
| 20 |  | 417 / 136 / 417 | 0 | app1=UP app2=UP app3=UP |
| 21 |  | 285 / 285 / 285 | 0 | app1=UP app2=UP app3=UP |
| 22 |  | 342 / 341 / 342 | 0 | app1=UP app2=UP app3=UP |
| 23 |  | 322 / 322 / 322 | 0 | app1=UP app2=UP app3=UP |
| 24 |  | 454 / 455 / 454 | 0 | app1=UP app2=UP app3=UP |
| 25 |  | 450 / 450 / 450 | 0 | app1=UP app2=UP app3=UP |
| 26 |  | 336 / 335 / 336 | 0 | app1=UP app2=UP app3=UP |
| 27 |  | 323 / 324 / 323 | 0 | app1=UP app2=UP app3=UP |
| 28 |  | 463 / 462 / 463 | 0 | app1=UP app2=UP app3=UP |
| 29 |  | 326 / 327 / 327 | 0 | app1=UP app2=UP app3=UP |

Усього запитів: 28652, успішних: 28652, помилок 5xx: 0, мережевих помилок: 0.
