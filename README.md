# Eisenhower Matrix Planner

![.NET 10](https://img.shields.io/badge/.NET-10-5C2D91?logo=.net&logoColor=white)
![WPF](https://img.shields.io/badge/WPF-512BD4?logo=dotnet&logoColor=white)
![MIT License](https://img.shields.io/github/license/farok/EisenhowerMatrix.Planner)
![Stars](https://img.shields.io/github/stars/farok/EisenhowerMatrix.Planner?style=social)

**A beautiful, modern and fully continuous Eisenhower Matrix built with WPF + .NET 10**

Unlike classic 4-quadrant apps, this planner uses a **smooth 10×10 priority grid** where every task is positioned exactly according to its real **Importance** and **Urgency** scores — no more "which quadrant?" guessing.


### Features

- Continuous 10×10 matrix (drag anywhere!)
- Live Importance & Urgency sliders (1–10)
- Smooth drag & drop with instant position update
- Auto-increase urgency when deadline is near
- "Today" view – instantly see what matters now
- In-Progress lane (max 4 tasks)
- Beautiful task cards with shadow and rounded corners
- 100% offline – SQLite persistence
- Clean Architecture + MVVM + SOLID + CommunityToolkit.Mvvm
- Zero external UI frameworks – pure WPF

### Tech Stack

- .NET 10 (LTS)
- WPF
- CommunityToolkit.Mvvm
- Entity Framework Core 10 + SQLite
- Microsoft.Extensions.DependencyInjection & Logging

### Installation (Windows 10/11)

1. Clone the repo
   ```bash
   git clone https://github.com/farok/EisenhowerMatrix.Planner.git
