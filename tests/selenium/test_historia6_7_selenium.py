import time
from datetime import date, timedelta

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://127.0.0.1:8000"


def slow(seconds: float = 1.5):
    """Pausa para o vídeo ficar mais legível."""
    time.sleep(seconds)


def login_as_admin(driver):
    """
    Faz login no Django Admin antes de usar as telas da aplicação.
    TROCAR PELO SEU USUÁRIO E SENHA DE SUPERUSER.
    """
    driver.get(f"{BASE_URL}/admin/login/")
    wait = WebDriverWait(driver, 15)

    user_input = wait.until(
        EC.presence_of_element_located((By.NAME, "username"))
    )
    pass_input = driver.find_element(By.NAME, "password")

    # >>> TROCAR AQUI PELO SEU SUPERUSER <<<
    user_input.send_keys("marco")
    pass_input.send_keys("1234567mA")

    slow()
    pass_input.send_keys(Keys.ENTER)

    wait.until(EC.url_contains("/admin/"))
    slow(2)


def criar_emprestimo_com_atraso(driver):
    """
    Cria um empréstimo via tela /livros/emprestimos/novo/
    para depois testar devolução com multa (História 6).
    Pressupõe que já exista:
      - pelo menos 1 livro
      - o usuário admin na base
    """
    wait = WebDriverWait(driver, 15)

    driver.get(f"{BASE_URL}/livros/emprestimos/novo/")
    slow(2)

    select_livro = wait.until(
        EC.presence_of_element_located((By.NAME, "livro_id"))
    )
    select_usuario = driver.find_element(By.NAME, "usuario_id")
    data_saida_input = driver.find_element(By.NAME, "data_saida")
    data_prevista_input = driver.find_element(By.NAME, "data_prevista_devolucao")

    # seleciona o primeiro livro
    select_livro.click()
    slow()
    select_livro.send_keys(Keys.ARROW_DOWN)
    slow()
    select_livro.send_keys(Keys.ENTER)
    slow()

    # seleciona o primeiro usuário (admin)
    select_usuario.click()
    slow()
    select_usuario.send_keys(Keys.ARROW_DOWN)
    slow()
    select_usuario.send_keys(Keys.ENTER)
    slow()

    hoje = date.today()
    data_saida = hoje - timedelta(days=5)
    data_prevista = hoje - timedelta(days=3)

    data_saida_input.clear()
    data_prevista_input.clear()
    data_saida_input.send_keys(data_saida.strftime("%Y-%m-%d"))
    slow()
    data_prevista_input.send_keys(data_prevista.strftime("%Y-%m-%d"))
    slow()

    data_prevista_input.send_keys(Keys.ENTER)

    wait.until(EC.url_contains("/livros/emprestimos/"))
    slow(2)


def devolver_com_multa(driver):
    """
    Entra na lista de empréstimos e registra devolução com atraso.
    Hist. 6 – cálculo de multa.
    """
    wait = WebDriverWait(driver, 15)

    driver.get(f"{BASE_URL}/livros/emprestimos/")
    slow(2)

    # primeira linha da tabela
    linha = wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "table tbody tr")
        )
    )
    slow()

    # Tenta achar link que tenha "Registrar" ou "Devolução" no texto
    btn_devolver = linha.find_element(
        By.XPATH,
        ".//a[contains(., 'Registrar') or contains(., 'Devolução') or contains(., 'devolução')]"
    )

    btn_devolver.click()
    slow(2)

    # tela de devolução
    data_devolucao_input = wait.until(
        EC.presence_of_element_located((By.NAME, "data_devolucao"))
    )

    hoje = date.today()
    data_devolucao_input.clear()
    data_devolucao_input.send_keys(hoje.strftime("%Y-%m-%d"))
    slow()
    data_devolucao_input.send_keys(Keys.ENTER)

    # volta pra lista + mensagem de multa
    wait.until(EC.url_contains("/livros/emprestimos/"))
    slow(3)


def gerar_relatorio(driver):
    """
    Vai até o Relatório de circulação (História 7) e
    emite um relatório simples para o período atual.
    """
    wait = WebDriverWait(driver, 15)

    driver.get(f"{BASE_URL}/livros/relatorios/circulacao/")
    slow(2)

    data_inicio_input = wait.until(
        EC.presence_of_element_located((By.NAME, "data_inicio"))
    )
    data_fim_input = driver.find_element(By.NAME, "data_fim")

    hoje = date.today()
    inicio = hoje - timedelta(days=30)

    data_inicio_input.clear()
    data_fim_input.clear()
    data_inicio_input.send_keys(inicio.strftime("%Y-%m-%d"))
    slow()
    data_fim_input.send_keys(hoje.strftime("%Y-%m-%d"))
    slow()
    data_fim_input.send_keys(Keys.ENTER)

    slow(3)


def exportar_relatorio(driver):
    """
    Clica nos botões de Exportar CSV e Exportar PDF do relatório (História 7),
    com pausas para ficar visível no vídeo.
    """
    wait = WebDriverWait(driver, 15)

    print("URL atual antes de exportar:", driver.current_url)
    slow(2)

    # --- Exportar CSV ---
    try:
        btn_csv = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//a[contains(., 'Exportar CSV') or contains(., 'CSV')]"
                    " | //button[contains(., 'Exportar CSV') or contains(., 'CSV')]"
                )
            )
        )
        slow()
        btn_csv.click()
        print("Cliquei em Exportar CSV")
        slow(3)
    except Exception as e:
        print("Não achei botão de CSV, seguindo assim mesmo:", e)

    # volta para tela de relatório (garante que fique igual ao que você mostrou)
    driver.get(f"{BASE_URL}/livros/relatorios/circulacao/")
    slow(2)

    # --- Exportar PDF ---
    try:
        btn_pdf = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//a[contains(., 'Exportar PDF') or contains(., 'PDF')]"
                    " | //button[contains(., 'Exportar PDF') or contains(., 'PDF')]"
                )
            )
        )
        slow()
        btn_pdf.click()
        print("Cliquei em Exportar PDF")
        slow(3)
    except Exception as e:
        print("Não achei botão de PDF, seguindo assim mesmo:", e)


def test_historia6_7_e2e():
    """
    Roteiro único para você gravar o vídeo:

    1. Abre o navegador
    2. Faz login no admin
    3. Cria um empréstimo atrasado
    4. Registra devolução com multa (História 6)
    5. Gera relatório e exporta CSV/PDF (História 7)
    """
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.maximize_window()

    try:
        login_as_admin(driver)
        criar_emprestimo_com_atraso(driver)
        devolver_com_multa(driver)
        gerar_relatorio(driver)
        exportar_relatorio(driver)

        
        slow(2)

    finally:
        driver.quit()
