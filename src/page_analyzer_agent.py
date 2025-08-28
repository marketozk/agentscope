"""
Page Analyzer Agent с ReAct парадигмой
Глубокий анализ веб-страниц для понимания структуры и планирования действий
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from agentscope.agent import ReActAgent
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit
from agentscope.message import Msg
from pydantic import BaseModel

class PageElement(BaseModel):
    """Информация об элементе страницы"""
    element_type: str
    selector: str
    text: str
    attributes: Dict[str, str]
    position: Dict[str, int]
    importance: float

class PageAnalysis(BaseModel):
    """Результат анализа страницы"""
    page_type: str  # registration, login, verification, profile, onboarding, etc.
    page_confidence: float
    main_action: Optional[str]  # что пользователь должен сделать
    interactive_elements: List[PageElement]
    forms_count: int
    navigation_options: List[str]
    error_messages: List[str]
    success_indicators: List[str]
    next_step_prediction: str
    reasoning: str

class PageAnalysisToolkit(Toolkit):
    """Инструменты для анализа страниц"""
    
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.register_tool_function(self.get_page_metadata)
        self.register_tool_function(self.analyze_page_structure)
        self.register_tool_function(self.identify_interactive_elements)
        self.register_tool_function(self.detect_page_type)
        self.register_tool_function(self.find_error_messages)
        self.register_tool_function(self.analyze_navigation_options)
        self.register_tool_function(self.detect_completion_indicators)
    
    async def get_page_metadata(self) -> str:
        """Получает базовые метаданные страницы"""
        try:
            metadata = await self.page.evaluate("""
                () => {
                    return {
                        title: document.title,
                        url: window.location.href,
                        domain: window.location.hostname,
                        path: window.location.pathname,
                        search: window.location.search,
                        hash: window.location.hash,
                        referrer: document.referrer,
                        language: document.documentElement.lang || 'unknown',
                        charset: document.characterSet,
                        ready_state: document.readyState,
                        viewport_width: window.innerWidth,
                        viewport_height: window.innerHeight,
                        scroll_width: document.documentElement.scrollWidth,
                        scroll_height: document.documentElement.scrollHeight,
                        last_modified: document.lastModified
                    };
                }
            """)
            
            # Добавляем мета-теги
            meta_tags = await self.page.evaluate("""
                () => {
                    const metas = {};
                    document.querySelectorAll('meta').forEach(meta => {
                        const name = meta.getAttribute('name') || meta.getAttribute('property') || meta.getAttribute('http-equiv');
                        const content = meta.getAttribute('content');
                        if (name && content) {
                            metas[name] = content;
                        }
                    });
                    return metas;
                }
            """)
            
            metadata['meta_tags'] = meta_tags
            
            return json.dumps(metadata, indent=2, ensure_ascii=False)
            
        except Exception as e:
            return f"Ошибка получения метаданных: {str(e)}"
    
    async def analyze_page_structure(self) -> str:
        """Анализирует структуру DOM страницы"""
        try:
            structure = await self.page.evaluate("""
                () => {
                    const analysis = {
                        total_elements: document.querySelectorAll('*').length,
                        headings: {},
                        semantic_elements: {},
                        interactive_elements: {},
                        media_elements: {},
                        text_content_length: document.body ? document.body.textContent.length : 0
                    };
                    
                    // Анализ заголовков
                    for (let i = 1; i <= 6; i++) {
                        const headings = document.querySelectorAll(`h${i}`);
                        if (headings.length > 0) {
                            analysis.headings[`h${i}`] = {
                                count: headings.length,
                                texts: Array.from(headings).slice(0, 3).map(h => h.textContent.trim().substring(0, 50))
                            };
                        }
                    }
                    
                    // Семантические элементы
                    const semantic_tags = ['header', 'nav', 'main', 'section', 'article', 'aside', 'footer'];
                    semantic_tags.forEach(tag => {
                        const count = document.querySelectorAll(tag).length;
                        if (count > 0) analysis.semantic_elements[tag] = count;
                    });
                    
                    // Интерактивные элементы
                    const interactive_selectors = {
                        'buttons': 'button, [role="button"]',
                        'links': 'a[href]',
                        'inputs': 'input, textarea, select',
                        'forms': 'form',
                        'checkboxes': 'input[type="checkbox"], input[type="radio"]'
                    };
                    
                    Object.entries(interactive_selectors).forEach(([name, selector]) => {
                        analysis.interactive_elements[name] = document.querySelectorAll(selector).length;
                    });
                    
                    // Медиа элементы
                    const media_selectors = {
                        'images': 'img',
                        'videos': 'video',
                        'audio': 'audio',
                        'iframes': 'iframe'
                    };
                    
                    Object.entries(media_selectors).forEach(([name, selector]) => {
                        analysis.media_elements[name] = document.querySelectorAll(selector).length;
                    });
                    
                    return analysis;
                }
            """)
            
            return json.dumps(structure, indent=2, ensure_ascii=False)
            
        except Exception as e:
            return f"Ошибка анализа структуры: {str(e)}"
    
    async def identify_interactive_elements(self) -> str:
        """Идентифицирует все интерактивные элементы с их свойствами"""
        try:
            elements = await self.page.evaluate("""
                () => {
                    const interactive_elements = [];
                    const selectors = [
                        'button, [role="button"]',
                        'a[href]',
                        'input, textarea, select',
                        '[onclick]',
                        '[data-action]',
                        '.btn, .button',
                        '[role="link"]'
                    ];
                    
                    const processed = new Set();
                    
                    selectors.forEach(selector => {
                        document.querySelectorAll(selector).forEach((element, index) => {
                            // Избегаем дублирования
                            if (processed.has(element)) return;
                            processed.add(element);
                            
                            const rect = element.getBoundingClientRect();
                            const styles = window.getComputedStyle(element);
                            
                            // Проверка видимости
                            const isVisible = rect.width > 0 && rect.height > 0 && 
                                            styles.visibility !== 'hidden' && 
                                            styles.display !== 'none' &&
                                            styles.opacity !== '0';
                            
                            if (!isVisible) return;
                            
                            const elementInfo = {
                                tag: element.tagName.toLowerCase(),
                                type: element.type || '',
                                text: element.textContent ? element.textContent.trim().substring(0, 100) : '',
                                id: element.id || '',
                                class: element.className || '',
                                name: element.name || '',
                                href: element.href || '',
                                value: element.value || '',
                                placeholder: element.placeholder || '',
                                aria_label: element.getAttribute('aria-label') || '',
                                data_attributes: {},
                                position: {
                                    x: Math.round(rect.x),
                                    y: Math.round(rect.y),
                                    width: Math.round(rect.width),
                                    height: Math.round(rect.height)
                                },
                                clickable: element.tagName.toLowerCase() === 'button' || 
                                          element.tagName.toLowerCase() === 'a' ||
                                          element.getAttribute('onclick') !== null ||
                                          element.getAttribute('role') === 'button',
                                focusable: element.tabIndex >= 0
                            };
                            
                            // Получаем data-* атрибуты
                            for (let attr of element.attributes) {
                                if (attr.name.startsWith('data-')) {
                                    elementInfo.data_attributes[attr.name] = attr.value;
                                }
                            }
                            
                            interactive_elements.push(elementInfo);
                        });
                    });
                    
                    return interactive_elements.slice(0, 50); // Ограничиваем количество
                }
            """)
            
            return json.dumps(elements, indent=2, ensure_ascii=False)
            
        except Exception as e:
            return f"Ошибка идентификации элементов: {str(e)}"
    
    async def detect_page_type(self) -> str:
        """Определяет тип страницы на основе содержимого"""
        try:
            detection_result = await self.page.evaluate("""
                () => {
                    const content = document.body.textContent.toLowerCase();
                    const title = document.title.toLowerCase();
                    const url = window.location.href.toLowerCase();
                    const combined = content + ' ' + title + ' ' + url;
                    
                    const page_types = {
                        'registration': {
                            keywords: ['register', 'sign up', 'create account', 'join', 'registration'],
                            forms: ['email', 'password', 'confirm'],
                            buttons: ['create', 'register', 'sign up'],
                            score: 0
                        },
                        'login': {
                            keywords: ['login', 'sign in', 'log in', 'authentication'],
                            forms: ['email', 'password', 'username'],
                            buttons: ['login', 'sign in', 'submit'],
                            score: 0
                        },
                        'verification': {
                            keywords: ['verify', 'verification', 'confirm', 'code', 'activate'],
                            forms: ['code', 'token', 'verify'],
                            buttons: ['verify', 'confirm', 'activate'],
                            score: 0
                        },
                        'profile_setup': {
                            keywords: ['profile', 'setup', 'information', 'details', 'complete'],
                            forms: ['name', 'company', 'phone', 'address'],
                            buttons: ['save', 'continue', 'next', 'complete'],
                            score: 0
                        },
                        'onboarding': {
                            keywords: ['welcome', 'getting started', 'tour', 'introduction', 'onboard'],
                            forms: [],
                            buttons: ['next', 'continue', 'start', 'skip'],
                            score: 0
                        },
                        'plan_selection': {
                            keywords: ['plan', 'pricing', 'subscription', 'choose', 'select'],
                            forms: [],
                            buttons: ['select', 'choose', 'upgrade', 'start'],
                            score: 0
                        },
                        'success': {
                            keywords: ['success', 'welcome', 'complete', 'done', 'finish'],
                            forms: [],
                            buttons: ['continue', 'dashboard', 'start'],
                            score: 0
                        },
                        'error': {
                            keywords: ['error', 'problem', 'issue', 'failed', 'wrong'],
                            forms: [],
                            buttons: ['retry', 'back', 'try again'],
                            score: 0
                        }
                    };
                    
                    // Подсчет очков для каждого типа
                    Object.keys(page_types).forEach(type => {
                        const config = page_types[type];
                        
                        // Очки за ключевые слова
                        config.keywords.forEach(keyword => {
                            const matches = (combined.match(new RegExp(keyword, 'g')) || []).length;
                            config.score += matches * 2;
                        });
                        
                        // Очки за наличие соответствующих форм
                        config.forms.forEach(field => {
                            if (document.querySelector(`input[type="${field}"], input[name*="${field}"], input[placeholder*="${field}"]`)) {
                                config.score += 3;
                            }
                        });
                        
                        // Очки за наличие соответствующих кнопок
                        config.buttons.forEach(button => {
                            if (document.querySelector(`button:contains("${button}"), input[value*="${button}"]`) ||
                                combined.includes(button)) {
                                config.score += 2;
                            }
                        });
                    });
                    
                    // Находим тип с максимальным счетом
                    let best_type = 'unknown';
                    let best_score = 0;
                    
                    Object.entries(page_types).forEach(([type, config]) => {
                        if (config.score > best_score) {
                            best_score = config.score;
                            best_type = type;
                        }
                    });
                    
                    return {
                        detected_type: best_type,
                        confidence: Math.min(best_score / 10, 1.0),
                        all_scores: Object.fromEntries(
                            Object.entries(page_types).map(([type, config]) => [type, config.score])
                        ),
                        analysis_text: combined.substring(0, 200)
                    };
                }
            """)
            
            return json.dumps(detection_result, indent=2, ensure_ascii=False)
            
        except Exception as e:
            return f"Ошибка определения типа страницы: {str(e)}"
    
    async def find_error_messages(self) -> str:
        """Находит сообщения об ошибках на странице"""
        try:
            errors = await self.page.evaluate("""
                () => {
                    const error_selectors = [
                        '.error, .errors',
                        '.alert-danger, .alert-error',
                        '.message-error',
                        '.validation-error',
                        '.form-error',
                        '[role="alert"]',
                        '.field-error',
                        '.input-error',
                        '[data-error]',
                        '.error-message',
                        '.warning'
                    ];
                    
                    const errors = [];
                    
                    error_selectors.forEach(selector => {
                        document.querySelectorAll(selector).forEach(element => {
                            const text = element.textContent.trim();
                            const styles = window.getComputedStyle(element);
                            
                            if (text && 
                                styles.display !== 'none' && 
                                styles.visibility !== 'hidden' &&
                                styles.opacity !== '0') {
                                
                                errors.push({
                                    text: text,
                                    selector: selector,
                                    element_id: element.id,
                                    element_class: element.className,
                                    severity: element.className.includes('danger') || 
                                             element.className.includes('error') ? 'high' : 'medium'
                                });
                            }
                        });
                    });
                    
                    // Поиск текста ошибок в содержимом
                    const error_keywords = ['error', 'invalid', 'required', 'missing', 'incorrect', 'failed', 'problem'];
                    const text_content = document.body.textContent.toLowerCase();
                    
                    error_keywords.forEach(keyword => {
                        if (text_content.includes(keyword)) {
                            // Найти элементы с этими словами
                            const xpath = `//text()[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '${keyword}')]`;
                            const result = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                            
                            for (let i = 0; i < Math.min(result.snapshotLength, 5); i++) {
                                const node = result.snapshotItem(i);
                                if (node && node.parentElement) {
                                    const text = node.textContent.trim();
                                    if (text.length > 10 && text.length < 200) {
                                        errors.push({
                                            text: text,
                                            selector: 'text_search',
                                            element_id: node.parentElement.id || '',
                                            element_class: node.parentElement.className || '',
                                            severity: 'low'
                                        });
                                    }
                                }
                            }
                        }
                    });
                    
                    return errors.slice(0, 10); // Ограничиваем количество
                }
            """)
            
            return json.dumps(errors, indent=2, ensure_ascii=False)
            
        except Exception as e:
            return f"Ошибка поиска ошибок: {str(e)}"
    
    async def analyze_navigation_options(self) -> str:
        """Анализирует варианты навигации на странице"""
        try:
            navigation = await self.page.evaluate("""
                () => {
                    const nav_options = [];
                    
                    // Поиск навигационных элементов
                    const nav_selectors = [
                        'nav a',
                        '.navigation a',
                        '.menu a',
                        '.navbar a',
                        'header a',
                        '.breadcrumb a',
                        '.pagination a',
                        'button[data-action]',
                        '[role="navigation"] a'
                    ];
                    
                    nav_selectors.forEach(selector => {
                        document.querySelectorAll(selector).forEach(element => {
                            const text = element.textContent.trim();
                            const href = element.href || element.getAttribute('data-action') || '';
                            
                            if (text && element.offsetParent !== null) { // проверка видимости
                                nav_options.push({
                                    text: text,
                                    href: href,
                                    type: element.tagName.toLowerCase(),
                                    selector: selector,
                                    is_external: href.startsWith('http') && !href.includes(window.location.hostname)
                                });
                            }
                        });
                    });
                    
                    // Поиск кнопок "Назад", "Далее", "Пропустить"
                    const action_buttons = [];
                    const action_keywords = ['back', 'next', 'continue', 'skip', 'previous', 'forward', 'cancel'];
                    
                    document.querySelectorAll('button, [role="button"], a').forEach(element => {
                        const text = element.textContent.toLowerCase().trim();
                        const hasActionKeyword = action_keywords.some(keyword => text.includes(keyword));
                        
                        if (hasActionKeyword && element.offsetParent !== null) {
                            action_buttons.push({
                                text: element.textContent.trim(),
                                action_type: action_keywords.find(keyword => text.includes(keyword)),
                                href: element.href || '',
                                tag: element.tagName.toLowerCase()
                            });
                        }
                    });
                    
                    return {
                        navigation_links: nav_options.slice(0, 20),
                        action_buttons: action_buttons.slice(0, 10),
                        total_links: document.querySelectorAll('a[href]').length,
                        total_buttons: document.querySelectorAll('button, [role="button"]').length
                    };
                }
            """)
            
            return json.dumps(navigation, indent=2, ensure_ascii=False)
            
        except Exception as e:
            return f"Ошибка анализа навигации: {str(e)}"
    
    async def detect_completion_indicators(self) -> str:
        """Ищет индикаторы завершения процесса"""
        try:
            indicators = await self.page.evaluate("""
                () => {
                    const success_indicators = [];
                    const progress_indicators = [];
                    
                    // Поиск индикаторов успеха
                    const success_selectors = [
                        '.success, .alert-success',
                        '.message-success',
                        '.confirmation',
                        '.complete, .completed',
                        '.welcome',
                        '[role="status"]',
                        '.check, .checkmark',
                        '.done'
                    ];
                    
                    success_selectors.forEach(selector => {
                        document.querySelectorAll(selector).forEach(element => {
                            const text = element.textContent.trim();
                            const styles = window.getComputedStyle(element);
                            
                            if (text && 
                                styles.display !== 'none' && 
                                styles.visibility !== 'hidden') {
                                
                                success_indicators.push({
                                    text: text.substring(0, 100),
                                    selector: selector,
                                    element_class: element.className
                                });
                            }
                        });
                    });
                    
                    // Поиск индикаторов прогресса
                    const progress_selectors = [
                        '.progress, .progress-bar',
                        '.step, .steps',
                        '.breadcrumb',
                        '.wizard',
                        '.stage, .stages',
                        '[role="progressbar"]'
                    ];
                    
                    progress_selectors.forEach(selector => {
                        document.querySelectorAll(selector).forEach(element => {
                            const text = element.textContent.trim();
                            const styles = window.getComputedStyle(element);
                            
                            if (styles.display !== 'none' && styles.visibility !== 'hidden') {
                                progress_indicators.push({
                                    text: text.substring(0, 50),
                                    selector: selector,
                                    aria_valuenow: element.getAttribute('aria-valuenow'),
                                    aria_valuemax: element.getAttribute('aria-valuemax')
                                });
                            }
                        });
                    });
                    
                    // Поиск ключевых слов успешного завершения
                    const success_keywords = ['congratulations', 'welcome', 'success', 'complete', 'done', 'finish', 'thank you'];
                    const content = document.body.textContent.toLowerCase();
                    const found_keywords = success_keywords.filter(keyword => content.includes(keyword));
                    
                    return {
                        success_indicators: success_indicators.slice(0, 10),
                        progress_indicators: progress_indicators.slice(0, 5),
                        success_keywords_found: found_keywords,
                        completion_confidence: found_keywords.length > 0 ? 0.8 : 0.2
                    };
                }
            """)
            
            return json.dumps(indicators, indent=2, ensure_ascii=False)
            
        except Exception as e:
            return f"Ошибка поиска индикаторов: {str(e)}"

class PageAnalyzerAgent(ReActAgent):
    """Интеллектуальный агент для анализа страниц"""
    
    def __init__(self, page, model):
        super().__init__(
            name="PageAnalyzerAgent",
            memory=InMemoryMemory(),
            model=model,
            tools=PageAnalysisToolkit(page)
        )
        self.page = page
    
    async def analyze_current_page(self) -> PageAnalysis:
        """Выполняет полный анализ текущей страницы"""
        
        # Системное сообщение для ReAct агента
        system_msg = Msg(
            role="system",
            content="""Ты - эксперт по анализу веб-страниц и UX.
            
            Твоя задача:
            1. Проанализировать структуру и содержимое страницы
            2. Определить тип страницы и её назначение
            3. Выявить основное действие, которое должен выполнить пользователь
            4. Найти все интерактивные элементы и возможности навигации
            5. Обнаружить ошибки или проблемы
            6. Предсказать следующий шаг в процессе
            
            Используй все доступные инструменты для полного анализа.
            Будь точным и детальным в своих выводах.
            Учитывай контекст регистрации или входа в систему."""
        )
        
        task_msg = Msg(
            role="user",
            content="Проанализируй текущую страницу полностью и предоставь детальный отчет о её структуре, назначении и рекомендуемых действиях."
        )
        
        # Запускаем ReAct процесс
        response = await self.call([system_msg, task_msg])
        
        # Собираем данные для результата
        try:
            # Определяем тип страницы
            page_type_data = await self.tools.detect_page_type()
            page_type_info = json.loads(page_type_data)
            
            # Получаем интерактивные элементы
            elements_data = await self.tools.identify_interactive_elements()
            elements = json.loads(elements_data)
            
            # Ищем ошибки
            errors_data = await self.tools.find_error_messages()
            errors = json.loads(errors_data)
            
            # Анализируем навигацию
            nav_data = await self.tools.analyze_navigation_options()
            navigation = json.loads(nav_data)
            
            # Ищем индикаторы завершения
            completion_data = await self.tools.detect_completion_indicators()
            completion = json.loads(completion_data)
            
            # Преобразуем элементы в PageElement объекты
            page_elements = []
            for elem in elements[:20]:  # Ограничиваем количество
                page_element = PageElement(
                    element_type=elem.get('tag', 'unknown'),
                    selector=f"{elem.get('tag', 'div')}" + (f"#{elem['id']}" if elem.get('id') else '') + (f".{elem['class'].split()[0]}" if elem.get('class') else ''),
                    text=elem.get('text', '')[:100],
                    attributes={
                        'type': elem.get('type', ''),
                        'class': elem.get('class', ''),
                        'id': elem.get('id', ''),
                        'name': elem.get('name', '')
                    },
                    position=elem.get('position', {}),
                    importance=0.8 if elem.get('clickable') else 0.5
                )
                page_elements.append(page_element)
            
            return PageAnalysis(
                page_type=page_type_info.get('detected_type', 'unknown'),
                page_confidence=page_type_info.get('confidence', 0.5),
                main_action=self._determine_main_action(page_type_info, elements),
                interactive_elements=page_elements,
                forms_count=len([e for e in elements if e.get('tag') == 'form']),
                navigation_options=[opt.get('text', '') for opt in navigation.get('navigation_links', [])],
                error_messages=[err.get('text', '') for err in errors],
                success_indicators=[ind.get('text', '') for ind in completion.get('success_indicators', [])],
                next_step_prediction=self._predict_next_step(page_type_info, elements, completion),
                reasoning=response.content if response else "Анализ выполнен"
            )
            
        except Exception as e:
            return PageAnalysis(
                page_type="error",
                page_confidence=0.0,
                main_action="unknown",
                interactive_elements=[],
                forms_count=0,
                navigation_options=[],
                error_messages=[str(e)],
                success_indicators=[],
                next_step_prediction="error_recovery",
                reasoning=f"Ошибка анализа: {str(e)}"
            )
    
    def _determine_main_action(self, page_type_info: Dict, elements: List[Dict]) -> str:
        """Определяет основное действие для пользователя"""
        page_type = page_type_info.get('detected_type', 'unknown')
        
        if page_type == 'registration':
            return "fill_registration_form"
        elif page_type == 'login':
            return "login"
        elif page_type == 'verification':
            return "enter_verification_code"
        elif page_type == 'profile_setup':
            return "complete_profile"
        elif page_type == 'onboarding':
            return "follow_onboarding_steps"
        elif page_type == 'plan_selection':
            return "select_plan"
        elif page_type == 'success':
            return "continue_to_dashboard"
        else:
            # Определяем по кнопкам
            buttons = [e for e in elements if e.get('tag') in ['button', 'input'] and e.get('type') in ['submit', 'button']]
            if buttons:
                return f"click_{buttons[0].get('text', 'button').lower()}"
            return "analyze_and_decide"
    
    def _predict_next_step(self, page_type_info: Dict, elements: List[Dict], completion: Dict) -> str:
        """Предсказывает следующий шаг"""
        page_type = page_type_info.get('detected_type', 'unknown')
        
        if completion.get('completion_confidence', 0) > 0.7:
            return "process_completed"
        
        if page_type == 'registration':
            return "email_verification_or_profile_setup"
        elif page_type == 'login':
            return "dashboard_or_profile"
        elif page_type == 'verification':
            return "profile_setup_or_onboarding"
        elif page_type == 'profile_setup':
            return "onboarding_or_plan_selection"
        elif page_type == 'onboarding':
            return "dashboard_access"
        elif page_type == 'plan_selection':
            return "payment_or_dashboard"
        else:
            return "continue_analysis"
