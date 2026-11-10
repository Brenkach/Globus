### Відмова вузла (kill app2)

| Секунда | Подія | Обслужили (app-1 / app-2 / app-3) | Помилки клієнта | Стан пулу в HAProxy |
|---|---|---|---|---|
| 0 |  | 370 / 370 / 369 | 0 | app1=UP app2=UP app3=UP |
| 1 |  | 323 / 323 / 324 | 0 | app1=UP app2=UP app3=UP |
| 2 |  | 326 / 326 / 325 | 0 | app1=UP app2=UP app3=UP |
| 3 |  | 301 / 302 / 303 | 0 | app1=UP app2=UP app3=UP |
| 4 |  | 456 / 455 / 455 | 0 | app1=UP app2=UP app3=UP |
| 5 | kill app2 | 487 / 60 / 486 | 0 | app1=UP app2=DOWN app3=UP |
| 6 |  | 474 / 0 / 474 | 0 | app1=UP app2=DOWN app3=UP |
| 7 |  | 439 / 0 / 440 | 0 | app1=UP app2=DOWN app3=UP |
| 8 |  | 552 / 0 / 552 | 0 | app1=UP app2=DOWN app3=UP |
| 9 |  | 357 / 0 / 357 | 0 | app1=UP app2=DOWN app3=UP |
| 10 |  | 533 / 0 / 533 | 0 | app1=UP app2=MAINT app3=UP |
| 11 |  | 564 / 0 / 565 | 0 | app1=UP app2=MAINT app3=UP |
| 12 |  | 306 / 0 / 304 | 0 | app1=UP app2=MAINT app3=UP |
| 13 |  | 605 / 0 / 605 | 0 | app1=UP app2=MAINT app3=UP |
| 14 |  | 438 / 0 / 438 | 0 | app1=UP app2=MAINT app3=UP |
| 15 | start app2 | 456 / 0 / 457 | 0 | app1=UP app2=MAINT app3=UP |
| 16 |  | 494 / 0 / 494 | 0 | app1=UP app2=MAINT app3=UP |
| 17 |  | 511 / 0 / 511 | 0 | app1=UP app2=DOWN app3=UP |
| 18 |  | 390 / 0 / 388 | 0 | app1=UP app2=DOWN app3=UP |
| 19 |  | 525 / 0 / 528 | 0 | app1=UP app2=DOWN app3=UP |
| 20 |  | 267 / 166 / 265 | 0 | app1=UP app2=UP app3=UP |
| 21 |  | 454 / 454 / 454 | 0 | app1=UP app2=UP app3=UP |
| 22 |  | 331 / 331 / 331 | 0 | app1=UP app2=UP app3=UP |
| 23 |  | 298 / 299 / 299 | 0 | app1=UP app2=UP app3=UP |
| 24 |  | 437 / 436 / 436 | 0 | app1=UP app2=UP app3=UP |
| 25 |  | 309 / 309 / 309 | 0 | app1=UP app2=UP app3=UP |
| 26 |  | 390 / 391 / 390 | 0 | app1=UP app2=UP app3=UP |
| 27 |  | 290 / 290 / 291 | 0 | app1=UP app2=UP app3=UP |
| 28 |  | 419 / 418 / 418 | 0 | app1=UP app2=UP app3=UP |
| 29 |  | 321 / 321 / 321 | 0 | app1=UP app2=UP app3=UP |

Усього запитів: 30096, успішних: 30096, помилок 5xx: 0, мережевих помилок: 0.
