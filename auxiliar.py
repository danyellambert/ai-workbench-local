# listas

lista_nova = []
nomes = ["Danyel", "Julia", "Maria"]
print(nomes[0])

nomes.append("Roberta")
print(nomes)

#dicionario

idades = {"Danyel": 31, "Julia": 24}
print(idades["Danyel"])
idades["Maria"]=25
idades["Danyel"] = 30
print(idades)

mensagem1 = {"role": "assistant", "content": "Bora terminar esse programa?"}
mensagem2 = {"role": "user", "content": "Bora !"}
mensagem3 = {"role": "assistant", "content": "Demorou !"}

lista_mensagens = [mensagem1, mensagem2, mensagem3]

nova_mensagem ={"role": "user", "content": "Opa ai sim !"}
lista_mensagens.append(nova_mensagem)


print(lista_mensagens)