# README

This repository demonstrates how to integrate **Large Language Models (LLMs)** with **VRExplorer** to reduce manual effort in **model abstraction** and **dataset analysis** for automated VR application testing. The workflow supports LLM-generated (or manually authored) test plans that can be imported, validated, and executed inside Unity.

## Features

- LLM-assisted test plan generation (with optional RAG support)
- Seamless integration with VRExplorer’s testing pipeline
- Automated ID binding and runtime execution via VRAgent
- Reproducible and configurable VR test execution in Unity

## Setup

### 1. Unity Configuration

- Use the **recommended Unity version** **(2021.3.45f1c2)** 

- Add Required Packages via Unity Package Manager. This project depends on the following Unity packages.
     Add them **via Git URL** in **Unity Package Manager**:

    1. Open **Unity Editor**
    2. Go to **Window → Package Manager**         <img src="Docs\4f72b677-b246-4b3e-8b92-e896fea4d7d8.png" alt="image-20251222122744225" style="zoom:33%;" />
    3. Click **`+` → Add package from git URL…**<img src="Docs\e1ddbed4-e99d-442e-94ae-f073a25551db.png" alt="image-20251222122744225" style="zoom:33%;" />
    4. Add the following packages:

    - **VRExplorer**

        ```
        https://github.com/TsingPig/VRExplorer_Release.git
        ```

        <img src="Docs\903bd5df-f96e-4659-93ca-3e6275d1c921.png" alt="image-20251222122744225" style="zoom:50%;" />

    - **VRAgent**

        ```
        https://github.com/TsingPig/VRAgent_Release.git
        ```

    After installation, ensure both packages are successfully loaded without errors.

### 2. Scene Preparation

1. Open or select the **scene to be tested** in Unity.

2. From the **Package** view, navigate to:<img src="Docs\21b88997-a1d8-4971-98e1-a0e65e3f99fb.png" alt="image-20251222122744225" style="zoom:33%;" />

    ```
    Packages → VRAgent
    ```

3. Drag the **VRAgent Prefab** into the selected scene.<img src="Docs\f2a695a1-e4e9-4f09-adfa-55e5f6d996fe.png" alt="image-20251222122744225" style="zoom:30%;" />

------

### 3. Navigation Mesh Baking

1. Select all static environment objects (e.g., walls, floors, obstacles).

2. Mark them as **Static** in the Inspector.
    <img src="Docs\9fa18dd5-1806-4b23-bd73-62dae6e22a34.png" alt="image-20251222122744225" style="zoom:33%;" />

3. Open the Navigation window:

    ```
    Window → AI → Navigation
    ```

    <img src="Docs\bfba4b5c-d2a0-48fb-bdb7-b06788a1c146.png" alt="image-20251222122744225" style="zoom:33%;" />

4. Bake the **NavMesh** for the scene.
    <img src="Docs\152bc526-eb60-4f45-a4a3-ae922f00f8d4.png" alt="image-20251222122744225" style="zoom:33%;" />

------

## Usage

### 1. *[Optional]* Test Plan Generation

Test plans can be prepared using:

- **LLM-based generation** (optionally enhanced with Retrieval-Augmented Generation), or
- **Manual configuration**, following the predefined test plan format.

The generated test plan is expected to be in a structured (e.g., JSON-based) format compatible with VRExplorer.

------

### 2. Import Test Plan

In the Unity Editor, import the test plan via: 

```
Tools → VRExplorer → Import Test Plan → Browse → Import Test Plan
```

<img src="Docs/d13a2dcd-1193-4310-8b5b-83f4ebd4c1bd.png" alt="d13a2dcd-1193-4310-8b5b-83f4ebd4c1bd" style="zoom:43%;" />

<img src="Docs/0c628c71-fc60-463e-9bca-1e2a04d6f26a.png" alt="0c628c71-fc60-463e-9bca-1e2a04d6f26a" style="zoom:50%;" />



------

### 3. Test Plan Validation

Before execution, verify that:

- A **FileIdManager** has been generated in the testing scene.<img src="Docs\f23fa1c193641069134af1cff847e2c7.png" alt="f23fa1c193641069134af1cff847e2c7" style="zoom:43%;" />
- All fileID mappings are correct and complete.
    <img src="Docs\8debdf7a-1f38-41a6-9d4d-bd3c8dcdcc73.png" alt="f23fa1c193641069134af1cff847e2c7" style="zoom:43%;" />

### *[Optional]* Code Coverage Recorading

#### 1. Install Unity Code Coverage Package

1. Open **Unity Editor**
2. Go to **Window → Package Manager**
3. Enable **Unity Registry**
4. Search for **Code Coverage**
5. Install the **Code Coverage** package provided by Unity

------

#### 2. Select Scripts for Coverage Collection

1. Open the Code Coverage window:

    ```
    Window → Analysis → Code Coverage
    ```

2. In the Code Coverage settings:

    - Select the **assemblies or scripts** to be included in coverage recording
    - Exclude unrelated or third-party code if necessary
