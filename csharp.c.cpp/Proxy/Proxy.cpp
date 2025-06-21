#include <string>

class ClientInfo {
public:
    std::string Endpoint; // Предполагаем, что Endpoint - строка в формате "IP:port"
    // ... другие члены класса
};

void EstablishP2P(ClientInfo& clientA, ClientInfo& clientB) {
    // Формируем сообщения для клиентов
    std::string messageToA = "P2P:" + clientB.Endpoint;
    std::string messageToB = "P2P:" + clientA.Endpoint;
    
    // Отправляем сообщения (предполагаем, что SendMessage реализована)
    SendMessage(clientA, messageToA);
    SendMessage(clientB, messageToB);
}

// Пример реализации SendMessage
void SendMessage(ClientInfo& client, const std::string& message) {
    
    std::cout << "Sending to " << client.Endpoint << ": " << message << std::endl;
}