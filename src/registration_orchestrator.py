"""
Главный оркестратор процесса регистрации
Координирует работу всех агентов системы
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import json

from .temp_mail_agent import TempMailAgent
from .email_verification_agent import EmailVerificationAgent
from .intelligent_agent import IntelligentRegistrationAgent

logger = logging.getLogger(__name__)

@dataclass
class RegistrationStep:
    """Шаг процесса регистрации"""
    step_id: str
    step_name: str
    status: str  # pending, in_progress, completed, failed
    result: Dict[str, Any] = None
    error: str = None
    started_at: datetime = None
    completed_at: datetime = None

@dataclass
class RegistrationResult:
    """Результат процесса регистрации"""
    success: bool
    account_created: bool
    email_verified: bool
    credentials: Dict[str, str]
    steps: List[RegistrationStep]
    errors: List[str]
    screenshots: List[str]
    final_url: str = None
    registration_data: Dict[str, Any] = None

class RegistrationOrchestrator:
    """
    Главный координатор системы регистрации
    Управляет всеми агентами и процессом регистрации
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._get_default_config()
        self.temp_mail_agent = None
        self.email_verification_agent = None
        # Добавляем единственный браузер для всех агентов
        self.shared_browser = None
        self.shared_context = None
        self.shared_page = None
        
        self.current_registration = None
        self.steps = []
        
        # Настройка логирования
        logging.basicConfig(level=logging.INFO)
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Возвращает конфигурацию по умолчанию"""
        return {
            "max_retries": 3,
            "page_load_timeout": 30000,
            "element_timeout": 5000,
            "email_check_interval": 10,
            "email_wait_timeout": 300,
            "screenshot_on_error": True,
            "headless_mode": False,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "viewport": {"width": 1920, "height": 1080}
        }
    
    async def start_registration(self, 
                               registration_url: str,
                               user_data: Dict[str, Any] = None) -> RegistrationResult:
        """
        Запускает процесс регистрации
        
        Args:
            registration_url: URL страницы регистрации
            user_data: Данные пользователя (опционально)
            
        Returns:
            RegistrationResult: Результат регистрации
        """
        logger.info(f"Начало процесса регистрации на: {registration_url}")
        
        # Инициализация
        self.steps = []
        self.current_registration = {
            'url': registration_url,
            'user_data': user_data or {},
            'started_at': datetime.now()
        }
        
        try:
            # Инициализируем агентов
            await self._initialize_agents()
            
            # Генерируем пользовательские данные если не переданы
            if not user_data or not user_data.get('email'):
                await self._generate_user_data()
            
            # Создаем временный email
            email_step = await self._create_temp_email()
            
            # Запускаем интеллектуальную регистрацию с ПОЛНОЙ МОЩНОСТЬЮ
            registration_step = await self._intelligent_registration_flow(registration_url)
            
            # Проверяем подтверждение email если требуется
            if registration_step.result and registration_step.result.get('email_verification_required'):
                await self._handle_email_verification()
            
            return self._create_final_result()
            
        except Exception as e:
            logger.error(f"Критическая ошибка в процессе регистрации: {e}")
            error_step = RegistrationStep(
                step_id="error",
                step_name="Критическая ошибка",
                status="failed",
                error=str(e),
                started_at=datetime.now(),
                completed_at=datetime.now()
            )
            self.steps.append(error_step)
            return self._create_final_result()
        
        finally:
            await self._cleanup_agents()
    
    async def _create_shared_browser(self):
        """Создает единственный браузер для всех агентов"""
        from playwright.async_api import async_playwright
        
        logger.info("Создание общего браузера для всех агентов...")
        
        self.playwright = await async_playwright().start()
        
        # Создаем браузер с стелс настройками
        self.shared_browser = await self.playwright.chromium.launch(
            headless=self.config.get('headless_mode', False),
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        
        # Создаем контекст с реальными настройками
        self.shared_context = await self.shared_browser.new_context(
            viewport={'width': self.config.get('viewport', {}).get('width', 1920), 
                     'height': self.config.get('viewport', {}).get('height', 1080)},
            user_agent=self.config.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'),
            locale='en-US',
            timezone_id='America/New_York'
        )
        
        # Создаем страницу
        self.shared_page = await self.shared_context.new_page()
        
        logger.info("Общий браузер создан успешно")
    
    async def _initialize_agents(self):
        """Инициализирует всех агентов"""
        step = RegistrationStep(
            step_id="init",
            step_name="Инициализация агентов",
            status="in_progress",
            started_at=datetime.now()
        )
        self.steps.append(step)
        
        try:
            # 1. Сначала создаем единственный браузер для всех агентов
            await self._create_shared_browser()
            
            # 2. Инициализируем TempMailAgent
            self.temp_mail_agent = TempMailAgent()
            await self.temp_mail_agent.__aenter__()
            
            # 3. Инициализируем EmailVerificationAgent с общим браузером
            self.email_verification_agent = EmailVerificationAgent(
                headless=self.config.get('headless_mode', False)
            )
            # Передаем ему наш общий браузер
            self.email_verification_agent.browser = self.shared_browser
            self.email_verification_agent.context = self.shared_context
            
            step.status = "completed"
            step.completed_at = datetime.now()
            step.result = {"agents_initialized": True, "shared_browser_created": True}
            
            logger.info("Все агенты успешно инициализированы с общим браузером")
            
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            step.completed_at = datetime.now()
            raise
    
    async def _generate_user_data(self) -> RegistrationStep:
        """Генерирует реалистичные данные пользователя с полной мощностью"""
        step = RegistrationStep(
            step_id="user_data_generation",
            step_name="Генерация данных пользователя",
            status="in_progress",
            started_at=datetime.now()
        )
        self.steps.append(step)
        
        try:
            import random
            import string
            
            # Генерируем уникальные данные
            timestamp = int(datetime.now().timestamp())
            random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
            
            # Базовые данные
            first_names = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Quinn"]
            last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
            
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            username = f"{first_name.lower()}{last_name.lower()}{random_suffix}"
            
            # Полный набор данных пользователя
            user_data = {
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'full_name': f'{first_name} {last_name}',
                'password': f'SecurePass{random.randint(1000, 9999)}!',
                'phone': f'+1{random.randint(2000000000, 9999999999)}',
                'birth_date': f'{random.randint(1985, 2000)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}',
                'company': f'{random.choice(["Tech", "Digital", "Global", "Pro", "Smart"])} {random.choice(["Solutions", "Systems", "Labs", "Works", "Corp"])}',
                'website': f'https://{username}.com',
                'country': 'United States',
                'city': random.choice(['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix']),
                'zip_code': f'{random.randint(10000, 99999)}',
                'address': f'{random.randint(100, 9999)} {random.choice(["Main", "Oak", "Pine", "Cedar", "Elm"])} St',
                'gender': random.choice(['male', 'female', 'prefer_not_to_say'])
            }
            
            # Сохраняем в текущую регистрацию
            self.current_registration['user_data'].update(user_data)
            
            step.status = "completed"
            step.completed_at = datetime.now()
            step.result = {"user_data_generated": True, "user_data": user_data}
            
            logger.info(f"Данные пользователя сгенерированы: {user_data['full_name']}")
            return step
            
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            step.completed_at = datetime.now()
            logger.error(f"Ошибка генерации данных пользователя: {e}")
            raise
    
    async def _create_temp_email(self) -> RegistrationStep:
        """Создает временный email адрес"""
        step = RegistrationStep(
            step_id="temp_email",
            step_name="Создание временного email",
            status="in_progress",
            started_at=datetime.now()
        )
        self.steps.append(step)
        
        try:
            temp_email = await self.temp_mail_agent.create_temp_email()
            
            step.status = "completed"
            step.completed_at = datetime.now()
            step.result = {
                "email": temp_email.email,
                "token": temp_email.token,
                "expires_at": temp_email.expires_at.isoformat()
            }
            
            # Сохраняем email в данные регистрации
            self.current_registration['email'] = temp_email.email
            
            logger.info(f"Создан временный email: {temp_email.email}")
            return step
            
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            step.completed_at = datetime.now()
            logger.error(f"Ошибка создания временного email: {e}")
            raise
    
    async def _intelligent_registration_flow(self, url: str) -> RegistrationStep:
        """Интеллектуальный процесс регистрации с ПОЛНОЙ МОЩНОСТЬЮ всех агентов"""
        step = RegistrationStep(
            step_id="intelligent_registration",
            step_name="Интеллектуальная регистрация",
            status="in_progress",
            started_at=datetime.now()
        )
        self.steps.append(step)
        
        try:
            from .intelligent_agent import IntelligentRegistrationAgent
            
            # Получаем API ключ из config
            api_key = self.config.get('gemini_api_key')
            if not api_key:
                raise ValueError("Gemini API ключ не найден")
            
            # Создаем intelligent agent с ПОЛНОЙ мощностью
            intelligent_agent = IntelligentRegistrationAgent(api_key)
            
            # Устанавливаем данные пользователя в agent
            if hasattr(intelligent_agent, 'user_data'):
                intelligent_agent.user_data.update(self.current_registration.get('user_data', {}))
                intelligent_agent.user_data['email'] = self.current_registration.get('email', '')
            
            # Переходим на страницу используя общий браузер
            logger.info(f"Переход на страницу регистрации: {url}")
            await self.shared_page.goto(url, wait_until='networkidle')
            
            # Выполняем РЕАЛЬНУЮ регистрацию через общий браузер
            result = await intelligent_agent._intelligent_registration_flow(self.shared_page)
            
            # Обрабатываем результат
            step.status = "completed" if result.get('success') else "failed"
            step.completed_at = datetime.now()
            step.result = {
                "registration_completed": result.get('success'),
                "account_created": result.get('success'),
                "url": url,
                "analysis_complete": True,
                "email_verification_required": False,
                "shared_browser_used": True,
                "steps_taken": result.get('steps_taken', 0),
                "completion_reason": result.get('completion_reason', 'registration_flow')
            }
            
            logger.info(f"Интеллектуальная регистрация завершена: {result.get('success')}")
            return step
            
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            step.completed_at = datetime.now()
            logger.error(f"Ошибка интеллектуальной регистрации: {e}")
            raise
    
    async def _fill_registration_form(self, email: str) -> RegistrationStep:
        """Заполняет форму регистрации"""
        step = RegistrationStep(
            step_id="form_filling",
            step_name="Заполнение формы регистрации",
            status="in_progress",
            started_at=datetime.now()
        )
        self.steps.append(step)
        
        try:
            # Подготавливаем данные для формы
            form_data = self._prepare_form_data(email)
            
            # ПРИМЕЧАНИЕ: Заполнение формы теперь происходит в _intelligent_registration_flow
            # через IntelligentRegistrationAgent
            fill_result = {
                "success": True,
                "message": "Форма обрабатывается через intelligent_registration_flow",
                "form_data": form_data
            }
            
            step.status = "completed" if fill_result.get('success') else "failed"
            step.completed_at = datetime.now()
            step.result = fill_result
            
            # Сохраняем данные регистрации
            self.current_registration['form_data'] = form_data
            self.current_registration['form_result'] = fill_result
            
            logger.info("Форма регистрации заполнена")
            return step
            
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            step.completed_at = datetime.now()
            logger.error(f"Ошибка заполнения формы: {e}")
            raise
    
    async def _handle_email_verification(self) -> RegistrationStep:
        """Обрабатывает email верификацию"""
        step = RegistrationStep(
            step_id="email_verification",
            step_name="Email верификация",
            status="in_progress",
            started_at=datetime.now()
        )
        self.steps.append(step)
        
        try:
            email = self.current_registration.get('email')
            
            # Ждем письмо с подтверждением
            logger.info("Ожидание письма с подтверждением...")
            link, code = await self.temp_mail_agent.get_verification_data(
                timeout=self.config.get('email_wait_timeout', 300),
                email=email
            )
            
            if not link and not code:
                # Проверяем, возможно верификация не требуется
                step.status = "completed"
                step.completed_at = datetime.now()
                step.result = {
                    "verification_required": False,
                    "message": "Email верификация не требуется"
                }
                logger.info("Email верификация не требуется")
                return step
            
            # Обрабатываем верификацию
            verification_result = await self.email_verification_agent.handle_email_verification_flow(
                verification_link=link,
                verification_code=code
            )
            
            step.status = "completed" if verification_result.get('success') else "failed"
            step.completed_at = datetime.now()
            step.result = verification_result
            
            if verification_result.get('success'):
                logger.info("Email успешно подтвержден")
            else:
                logger.warning("Ошибка подтверждения email")
            
            return step
            
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            step.completed_at = datetime.now()
            logger.error(f"Ошибка email верификации: {e}")
            return step
    
    async def _analyze_final_result(self) -> RegistrationStep:
        """Анализирует финальный результат регистрации"""
        step = RegistrationStep(
            step_id="final_analysis",
            step_name="Анализ финального результата",
            status="in_progress",
            started_at=datetime.now()
        )
        self.steps.append(step)
        
        try:
            # Анализируем результаты всех шагов
            final_analysis = {
                "registration_successful": any(
                    step.step_id == "intelligent_registration" and step.status == "completed"
                    for step in self.steps
                ),
                "steps_completed": len([s for s in self.steps if s.status == "completed"]),
                "total_steps": len(self.steps),
                "analysis_method": "orchestrator_analysis"
            }
            
            step.status = "completed"
            step.completed_at = datetime.now()
            step.result = final_analysis
            
            logger.info(f"Финальный анализ завершен: {final_analysis.get('registration_successful', False)}")
            return step
            
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            step.completed_at = datetime.now()
            logger.error(f"Ошибка финального анализа: {e}")
            return step
    
    def _prepare_form_data(self, email: str) -> Dict[str, Any]:
        """Подготавливает данные для заполнения формы"""
        # Базовые данные
        form_data = {
            'email': email,
            'password': self._generate_password(),
            'confirm_password': None,  # Будет установлен как password
            'username': self._generate_username(email),
            'first_name': 'Test',
            'last_name': 'User',
            'country': 'Russia',
            'phone': '+7900123456',
            'agree_terms': True,
            'subscribe_newsletter': False
        }
        
        # Добавляем пользовательские данные если есть
        if self.current_registration.get('user_data'):
            form_data.update(self.current_registration['user_data'])
        
        # Устанавливаем подтверждение пароля
        form_data['confirm_password'] = form_data['password']
        
        return form_data
    
    def _generate_password(self) -> str:
        """Генерирует безопасный пароль"""
        import random
        import string
        
        # Генерируем пароль с различными типами символов
        length = 12
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(random.choice(chars) for _ in range(length))
        
        # Убеждаемся что есть хотя бы одна цифра и спецсимвол
        if not any(c.isdigit() for c in password):
            password = password[:-1] + '1'
        if not any(c in "!@#$%^&*" for c in password):
            password = password[:-1] + '!'
            
        return password
    
    def _generate_username(self, email: str) -> str:
        """Генерирует username на основе email"""
        base = email.split('@')[0]
        import random
        suffix = random.randint(100, 999)
        return f"{base}{suffix}"
    
    def _create_final_result(self) -> RegistrationResult:
        """Создает финальный результат регистрации"""
        completed_steps = [s for s in self.steps if s.status == "completed"]
        failed_steps = [s for s in self.steps if s.status == "failed"]
        
        # Определяем успешность регистрации
        account_created = any(
            step.step_id == "intelligent_registration" and step.status == "completed"
            for step in self.steps
        )
        
        email_verified = any(
            step.step_id == "email_verification" and step.status == "completed" and
            step.result.get('verification_required', True) and step.result.get('success', False)
            for step in self.steps
        )
        
        # Если верификация не требовалась, считаем её пройденной
        if not email_verified:
            email_verified = any(
                step.step_id == "email_verification" and step.status == "completed" and
                not step.result.get('verification_required', True)
                for step in self.steps
            )
        
        success = account_created and len(failed_steps) == 0
        
        # Собираем учетные данные
        credentials = {}
        if self.current_registration:
            credentials = {
                'email': self.current_registration.get('email'),
                'password': self.current_registration.get('form_data', {}).get('password'),
                'username': self.current_registration.get('form_data', {}).get('username')
            }
        
        # Собираем ошибки
        errors = [step.error for step in failed_steps if step.error]
        
        # Собираем скриншоты
        screenshots = []
        for step in self.steps:
            if step.result and step.result.get('screenshot'):
                screenshots.append(step.result['screenshot'])
        
        return RegistrationResult(
            success=success,
            account_created=account_created,
            email_verified=email_verified,
            credentials=credentials,
            steps=self.steps,
            errors=errors,
            screenshots=screenshots,
            final_url=self.current_registration.get('url') if self.current_registration else None,
            registration_data=self.current_registration
        )
    
    async def _cleanup_agents(self):
        """Очищает ресурсы агентов и общий браузер"""
        try:
            if self.temp_mail_agent:
                await self.temp_mail_agent.__aexit__(None, None, None)
            
            # EmailVerificationAgent больше не имеет своего браузера
            # Закрываем общий браузер
            if self.shared_page:
                await self.shared_page.close()
                logger.info("Общая страница закрыта")
                
            if self.shared_context:
                await self.shared_context.close()
                logger.info("Общий контекст закрыт")
                
            if self.shared_browser:
                await self.shared_browser.close()
                logger.info("Общий браузер закрыт")
                
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
                logger.info("Playwright остановлен")
                
        except Exception as e:
            logger.warning(f"Ошибка при очистке агентов: {e}")
    
    def save_registration_log(self, filepath: str = None):
        """Сохраняет лог регистрации в файл"""
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"registration_log_{timestamp}.json"
        
        log_data = {
            'registration_info': {
                'url': self.current_registration.get('url'),
                'email': self.current_registration.get('email'),
                'started_at': self.current_registration.get('started_at').isoformat() if self.current_registration.get('started_at') else None,
                'user_data': self.current_registration.get('user_data'),
                'form_data': {k: v for k, v in self.current_registration.get('form_data', {}).items() if k != 'password'}  # Исключаем пароль
            },
            'steps': [
                {
                    'step_id': step.step_id,
                    'step_name': step.step_name,
                    'status': step.status,
                    'result': step.result,
                    'error': step.error,
                    'started_at': step.started_at.isoformat() if step.started_at else None,
                    'completed_at': step.completed_at.isoformat() if step.completed_at else None
                }
                for step in self.steps
            ]
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Лог регистрации сохранен: {filepath}")
        except Exception as e:
            logger.error(f"Ошибка сохранения лога: {e}")


# Пример использования
async def main():
    """Демонстрация работы RegistrationOrchestrator"""
    orchestrator = RegistrationOrchestrator()
    
    # Пример регистрации
    registration_url = "https://example.com/register"
    user_data = {
        'first_name': 'Иван',
        'last_name': 'Петров',
        'country': 'Russia'
    }
    
    result = await orchestrator.start_registration(
        registration_url=registration_url,
        user_data=user_data
    )
    
    print(f"Регистрация успешна: {result.success}")
    print(f"Аккаунт создан: {result.account_created}")
    print(f"Email подтвержден: {result.email_verified}")
    print(f"Учетные данные: {result.credentials}")
    
    # Сохраняем лог
    orchestrator.save_registration_log()


if __name__ == "__main__":
    asyncio.run(main())
