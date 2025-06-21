using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Sockets;
using System.Threading.Tasks;

namespace IPSetOptimization
{
    class Optimization
    {
        static async Task Main(string[] args)
        {
            if (args.Length == 0)
            {
                Console.WriteLine("Usage: IPSetGenerator <url1> [url2] ...");
                Console.WriteLine("Example: IPSetGenerator https://google.com https://cloudflare.com");
                return;
            }

            var generator = new IPSetGenerator();
            await generator.ProcessDomainsAsync(args);
        }
    }

    public class IPSetGenerator
    {
        private readonly ConcurrentDictionary<string, IPAddress[]> _dnsCache = 
            new ConcurrentDictionary<string, IPAddress[]>();
        
        private readonly HttpClient _httpClient = new HttpClient
        {
            Timeout = TimeSpan.FromSeconds(5)
        };

        public async Task ProcessDomainsAsync(IEnumerable<string> urls)
        {
            var tasks = urls.Select(ProcessDomainAsync);
            var results = await Task.WhenAll(tasks);
            
            foreach (var commands in results.Where(c => !string.IsNullOrEmpty(c)))
            {
                Console.WriteLine(commands);
                Console.WriteLine();
            }
        }

        private async Task<string> ProcessDomainAsync(string url)
        {
            try
            {
                var domain = ExtractDomain(url);
                var ips = await ResolveDnsWithFallbackAsync(domain);
                var ipv4Addresses = FilterIPv4Addresses(ips);
                
                if (!ipv4Addresses.Any())
                    return $"# No IPv4 addresses found for {domain}";

                return GenerateCommands(domain, ipv4Addresses);
            }
            catch (Exception ex)
            {
                return $"# Error processing {url}: {ex.Message}";
            }
        }

        private string ExtractDomain(string input)
        {
            if (Uri.TryCreate(input, UriKind.Absolute, out var uri) ||
                Uri.TryCreate("https://" + input, UriKind.Absolute, out uri))
            {
                return uri.Host.StartsWith("www.") 
                    ? uri.Host[4..] 
                    : uri.Host;
            }
            return input.Split('/')[0].Replace("www.", "");
        }

        private async Task<IPAddress[]> ResolveDnsWithFallbackAsync(string domain)
        {
            // Кеширование результатов
            if (_dnsCache.TryGetValue(domain, out var cached))
                return cached;

            try
            {
                // Основной DNS-запрос
                var addresses = await Dns.GetHostAddressesAsync(domain);
                _dnsCache[domain] = addresses;
                return addresses;
            }
            catch (SocketException)
            {
                try
                {
                    // Fallback через DoH (DNS-over-HTTPS)
                    var json = await _httpClient.GetStringAsync(
                        $"https://cloudflare-dns.com/dns-query?name={domain}&type=A");
                    
                    var ips = json.Split("\"data\":")
                        .Skip(1)
                        .Select(p => p.Split('"')[1])
                        .Where(ip => IPAddress.TryParse(ip, out _))
                        .Select(ip => IPAddress.Parse(ip))
                        .ToArray();

                    _dnsCache[domain] = ips;
                    return ips;
                }
                catch
                {
                    return Array.Empty<IPAddress>();
                }
            }
        }

        private IPAddress[] FilterIPv4Addresses(IPAddress[] addresses) 
            => addresses.Where(ip => ip.AddressFamily == AddressFamily.InterNetwork).ToArray();

        private string GenerateCommands(string domain, IPAddress[] ipv4Addresses)
        {
            var setName = GenerateSetName(domain);
            var timestamp = DateTime.UtcNow.ToString("yyyy-MM-dd HH:mm:ss UTC");
            
            var commands = new List<string>
            {
                $"# IPSet commands for: {domain}",
                $"# Generated at: {timestamp}",
                $"# IPv4 addresses found: {ipv4Addresses.Length}",
                "",
                "# Create ipset (if not exists)",
                $"sudo ipset create {setName} hash:ip --exist",
                "",
                "# Flush existing entries",
                $"sudo ipset flush {setName}",
                "",
                "# Add IP addresses"
            };

            commands.AddRange(ipv4Addresses.Select(ip => 
                $"sudo ipset add {setName} {ip} 2>/dev/null"));

            commands.AddRange(new[]
            {
                "",
                "# Apply iptables rules",
                $"sudo iptables -A OUTPUT -m set --match-set {setName} dst -j ACCEPT",
                "",
                "# For automatic updates, add to crontab:",
                $"# 0 3 * * * {Environment.ProcessPath} {domain} > /path/to/update_{setName}.sh"
            });

            return string.Join(Environment.NewLine, commands);
        }

        private string GenerateSetName(string domain)
        {
            var clean = new string(domain
                .Where(c => char.IsLetterOrDigit(c) || c == '.')
                .ToArray())
                .Replace('.', '_');
            
            return $"{clean[..Math.Min(clean.Length, 28)]}_set";
        }
    }
}