# Architecture & Developer Documentation

## 🏗️ System Architecture & Import Graph
This diagram shows the relationship and import dependencies between modules in the codebase.

```mermaid
graph TD

  
    
  
    
  
    
  
    
  
    
  
    
  
    
  
    
  
    
  
    
  
    
  
    
  
    
  
    
  
    
  
    
  
    
  
    
  
    
  
    
  

```

---

## 📁 File Reference Catalog


### 📄 `app.py`
- **Language:** python
- **Lines of Code:** 30





#### Functions
| Function Name | Line | Async | Arguments | Return Type | Description |
|---|---|---|---|---|---|

| `create_app` | 10 | False |  | `Any` | No description. |



---

### 📄 `config.py`
- **Language:** python
- **Lines of Code:** 9



#### Classes
| Class Name | Line | Inherits From | Description |
|---|---|---|---|

| `Config` | 3 |  | No description. |









---

### 📄 `controllers/page_controller.py`
- **Language:** python
- **Lines of Code:** 56





#### Functions
| Function Name | Line | Async | Arguments | Return Type | Description |
|---|---|---|---|---|---|

| `home` | 10 | False |  | `Any` | No description. |

| `tasks_ui` | 14 | False |  | `Any` | No description. |

| `schedule_ui` | 23 | False |  | `Any` | No description. |



---

### 📄 `controllers/schedule_controller.py`
- **Language:** python
- **Lines of Code:** 11





#### Functions
| Function Name | Line | Async | Arguments | Return Type | Description |
|---|---|---|---|---|---|

| `get_schedule` | 7 | False |  | `Any` | No description. |



---

### 📄 `controllers/task_controller.py`
- **Language:** python
- **Lines of Code:** 28





#### Functions
| Function Name | Line | Async | Arguments | Return Type | Description |
|---|---|---|---|---|---|

| `get_tasks` | 10 | False |  | `Any` | No description. |

| `set_effort` | 17 | False |  | `Any` | No description. |



---

### 📄 `controllers/__init__.py`
- **Language:** python
- **Lines of Code:** 0






---

### 📄 `models/schedule.py`
- **Language:** python
- **Lines of Code:** 13



#### Classes
| Class Name | Line | Inherits From | Description |
|---|---|---|---|

| `DaySchedule` | 1 |  | No description. |




##### Methods inside `DaySchedule`
| Method Name | Line | Async | Arguments | Return Type |
|---|---|---|---|---|

| `__init__` | 2 | False | `self`, `date` | `Any` |

| `add_task` | 6 | False | `self`, `task` | `Any` |

| `to_dict` | 9 | False | `self` | `Any` |







---

### 📄 `models/task.py`
- **Language:** python
- **Lines of Code:** 39



#### Classes
| Class Name | Line | Inherits From | Description |
|---|---|---|---|

| `Task` | 5 |  | No description. |




##### Methods inside `Task`
| Method Name | Line | Async | Arguments | Return Type |
|---|---|---|---|---|

| `__init__` | 8 | False | `self`, `id`, `name`, `effort` | `Any` |

| `_load_store` | 12 | False | `cls` | `Any` |

| `_save_store` | 21 | False | `cls` | `Any` |

| `from_dict` | 27 | False | `cls`, `d` | `Any` |

| `get` | 31 | False | `cls`, `task_id` | `Any` |

| `save` | 34 | False | `self` | `Any` |

| `to_dict` | 38 | False | `self` | `Any` |







---

### 📄 `models/__init__.py`
- **Language:** python
- **Lines of Code:** 0






---

### 📄 `services/asana_service.py`
- **Language:** python
- **Lines of Code:** 0






---

### 📄 `services/scheduling.py`
- **Language:** python
- **Lines of Code:** 38





#### Functions
| Function Name | Line | Async | Arguments | Return Type | Description |
|---|---|---|---|---|---|

| `generate_schedule` | 5 | False | `start_date_str`, `daily_limit`, `algorithm` | `Any` | No description. |



---

### 📄 `services/trello_service.py`
- **Language:** python
- **Lines of Code:** 46





#### Functions
| Function Name | Line | Async | Arguments | Return Type | Description |
|---|---|---|---|---|---|

| `_load_local_tasks` | 14 | False |  | `Any` | Load tasks from local fallback file task_data.json |

| `fetch_tasks_from_trello` | 27 | False |  | `Any` | Fetch tasks (Trello cards) from Trello API.
Falls back to local task_data.json on any error. |



---

### 📄 `services/__init__.py`
- **Language:** python
- **Lines of Code:** 0






---

### 📄 `tests/test_schedule.py`
- **Language:** python
- **Lines of Code:** 0






---

### 📄 `tests/test_tasks.py`
- **Language:** python
- **Lines of Code:** 0






---

### 📄 `tests/__init__.py`
- **Language:** python
- **Lines of Code:** 0






---

### 📄 `views/templates/base.html`
- **Language:** html
- **Lines of Code:** 57

- **Details:** HTML Document. Links: 4, Forms: 0






---

### 📄 `views/templates/home.html`
- **Language:** html
- **Lines of Code:** 161

- **Details:** HTML Document. Links: 3, Forms: 0






---

### 📄 `views/templates/schedule.html`
- **Language:** html
- **Lines of Code:** 90

- **Details:** HTML Document. Links: 5, Forms: 0






---

### 📄 `views/templates/tasks.html`
- **Language:** html
- **Lines of Code:** 125

- **Details:** HTML Document. Links: 0, Forms: 0






---


---
*DEVELOPER.md generated automatically by [CodeAtlas](https://github.com/your-repo/codeatlas) with zero LLM calls.*