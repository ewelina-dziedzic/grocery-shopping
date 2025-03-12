# Grocery Shopping Assistant 🤖🛒

> [!WARNING]
>
> ⚠️ Deprecated: This repository is no longer maintained. It has been rewritten in C# for improved type safety and performance.
>
> 👉 Check out the new version [here](https://github.com/ewelina-dziedzic/grocery-shopping-dotnet).

This project automates the process of grocery shopping by leveraging low-code tools, custom scripts, and AI. It streamlines grocery list generation, scheduling of groceries delivery, and online shopping cart population, saving time, reducing food waste, and eliminating repetitive tasks.

Using a combination of platforms like Notion, Make.com, and AWS Lambda, alongside an LLM (Large Language Model), the system ensures personalized grocery shopping based on your meal plan and ad-hoc grocery needs.

This repository contains custom code for managing grocery shopping lists, scheduling deliveries with my preferred online store and automating the process of populating my shopping cart.

![assistant animation](assistant-animation.gif)

## Technology Stack
- **Make.com**: Workflow automation platform to trigger AWS Lambda functions and manage data flow.
- **Telegram Bot**: User interface for interaction and notifications.
- **Notion**: Meal planning and recipes management.
- **Todoist**: Managing additional grocery needs.
- **AWS Lambda**: Serverless functions to handle custom logic.
- **Python**: Custom scripting and logic.
- **Online Grocery Store API**: Interface for managing shopping cart operations.
- **ChatGPT**: Acts as a decision-making assistant, responsible for analyzing provided options and selecting the best product based on my preferences. 
- **GitHub Actions**: Continuous Integration and Deployment (CI/CD).
