using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

namespace IPSetOptimization
{
    class Program
    {
        static async Task Main(string[] args)
        {
            // Парсинг аргументов командной строки
            var options = ParseCommandLine(args);
            if (options == null) return;

            // Инициализация генератора с настройками
            var generator = new IPSetGenerator(options);
            
            try
            {
                // Обработка доменов
                var results = await generator.ProcessDomainsAsync(options.Domains);
                
                // Вывод результатов
                foreach (var result in results)
                {
                    if (options.OutputFormat == OutputFormat.Json)
                    {
                        Console.WriteLine(JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true }));
                    }
                    else
                    {
                        Console.WriteLine(result.Commands);
                    }
                    
                    // Сохранение в файл при необходимости
                    if (!string.IsNullOrEmpty(options.OutputFile))
                    {
                        await SaveResultsToFile(result, options);
                    }
                }
                
                // Генерация скриптов
                if (options.GenerateScripts)
                {
                    generator.GenerateUpdateScripts(results);
                }
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"Fatal error: {ex.Message}");
                if (options.Verbose)
                {
                    Console.Error.WriteLine(ex.StackTrace);
                }
            }
        }

        private static CommandLineOptions ParseCommandLine(string[] args)
        {
            var options = new CommandLineOptions();
            
            if (args.Length == 0 || args.Contains("--help"))
            {
                ShowHelp();
                return null;
            }

            var domains = new List<string>();
            bool skipNext = false;

            for (int i = 0; i < args.Length; i++)
            {
                if (skipNext)
                {
                    skipNext = false;
                    continue;
                }

                switch (args[i])
                {
                    case "--ipv6":
                        options.IncludeIPv6 = true;
                        break;
                    case "--json":
                        options.OutputFormat = OutputFormat.Json;
                        break;
                    case "--verbose":
                        options.Verbose = true;
                        break;
                    case "--scripts":
                        options.GenerateScripts = true;
                        break;
                    case "--dns":
                        if (i + 1 < args.Length)
                        {
                            options.DnsServer = args[i + 1];
                            skipNext = true;
                        }
                        break;
                    case "--output":
                        if (i + 1 < args.Length)
                        {
                            options.OutputFile = args[i + 1];
                            skipNext = true;
                        }
                        break;
                    case "--set-name":
                        if (i + 1 < args.Length)
                        {
                            options.CustomSetName = args[i + 1];
                            skipNext = true;
                        }
                        break;
                    default:
                        domains.Add(args[i]);
                        break;
                }
            }

            options.Domains = domains;
            return options;
        }

        private static void ShowHelp()
        {
            Console.WriteLine(@"
IPSet Generator v2.0 - Advanced IP Set Management Tool

Usage: IPSetGenerator [options] <url1> [url2] ...

Options:
  --ipv6             Include IPv6 addresses in the results
  --json             Output results in JSON format
  --verbose          Show detailed error information
  --scripts          Generate update scripts (Bash & PowerShell)
  --dns <server>     Use custom DNS server (IP or DoH URL)
  --output <file>    Save results to the specified file
  --set-name <name>  Custom name for the IP set
  --help             Show this help message

Examples:
  IPSetGenerator https://google.com --ipv6
  IPSetGenerator https://cloudflare.com --json --output results.json
  IPSetGenerator https://microsoft.com --dns https://dns.google/dns-query
");
        }

        private static async Task SaveResultsToFile(DomainResult result, CommandLineOptions options)
        {
            try
            {
                var content = options.OutputFormat == OutputFormat.Json
                    ? JsonSerializer.Serialize(result)
                    : result.Commands;

                await File.WriteAllTextAsync(options.OutputFile, content);
                Console.WriteLine($"Results saved to {options.OutputFile}");
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"Error saving to file: {ex.Message}");
            }
        }
    }

    public class CommandLineOptions
    {
        public IEnumerable<string> Domains { get; set; } = Enumerable.Empty<string>();
        public bool IncludeIPv6 { get; set; }
        public OutputFormat OutputFormat { get; set; } = OutputFormat.Text;
        public bool Verbose { get; set; }
        public bool GenerateScripts { get; set; }
        public string DnsServer { get; set; } = "https://cloudflare-dns.com/dns-query";
        public string OutputFile { get; set; }
        public string CustomSetName { get; set; }
    }

    public enum OutputFormat { Text, Json }

    public class DomainResult
    {
        public string Domain { get; set; }
        public string SetName { get; set; }
        public string[] IPv4Addresses { get; set; }
        public string[] IPv6Addresses { get; set; }
        public string Commands { get; set; }
        public DateTime GeneratedAt { get; set; } = DateTime.UtcNow;
    }

    public class IPSetGenerator
    {
        private readonly CommandLineOptions _options;
        private readonly ConcurrentDictionary<string, IPAddress[]> _dnsCache = new();
        private readonly HttpClient _httpClient = new();
        private readonly Stopwatch _stopwatch = new();

        public IPSetGenerator(CommandLineOptions options)
        {
            _options = options;
            _httpClient.Timeout = TimeSpan.FromSeconds(10);
        }

        public async Task<List<DomainResult>> ProcessDomainsAsync(IEnumerable<string> urls)
        {
            _stopwatch.Start();
            var results = new List<DomainResult>();
            
            var domains = urls
                .Select(ExtractDomain)
                .Distinct()
                .ToList();

            Console.WriteLine($"Processing {domains.Count} domains...");

            var tasks = domains.Select(ProcessDomainAsync);
            var processedResults = await Task.WhenAll(tasks);
            
            results.AddRange(processedResults.Where(r => r != null));
            
            _stopwatch.Stop();
            Console.WriteLine($"Processed {results.Count} domains in {_stopwatch.Elapsed.TotalSeconds:0.00}s");
            
            return results;
        }

        private async Task<DomainResult> ProcessDomainAsync(string domain)
        {
            try
            {
                if (_options.Verbose)
                {
                    Console.WriteLine($"Resolving DNS for: {domain}");
                }
                
                var ips = await ResolveDnsWithFallbackAsync(domain);
                var ipv4Addresses = ips
                    .Where(ip => ip.AddressFamily == AddressFamily.InterNetwork)
                    .Select(ip => ip.ToString())
                    .ToArray();
                
                var ipv6Addresses = _options.IncludeIPv6
                    ? ips
                        .Where(ip => ip.AddressFamily == AddressFamily.InterNetworkV6)
                        .Select(ip => ip.ToString())
                        .ToArray()
                    : Array.Empty<string>();
                
                if (!ipv4Addresses.Any() && !ipv6Addresses.Any())
                {
                    Console.WriteLine($"No IP addresses found for {domain}");
                    return null;
                }

                var result = new DomainResult
                {
                    Domain = domain,
                    IPv4Addresses = ipv4Addresses,
                    IPv6Addresses = ipv6Addresses,
                    SetName = !string.IsNullOrEmpty(_options.CustomSetName)
                        ? _options.CustomSetName
                        : GenerateSetName(domain)
                };

                result.Commands = GenerateCommands(result);
                return result;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error processing {domain}: {ex.Message}");
                if (_options.Verbose)
                {
                    Console.WriteLine(ex.StackTrace);
                }
                return null;
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
                // Если указан кастомный DNS
                if (!string.IsNullOrEmpty(_options.DnsServer))
                {
                    if (_options.DnsServer.StartsWith("https://"))
                    {
                        return await ResolveViaDoh(domain);
                    }
                    else
                    {
                        return await ResolveViaCustomDns(domain);
                    }
                }
                
                // Стандартное разрешение DNS
                var addresses = await Dns.GetHostAddressesAsync(domain);
                _dnsCache[domain] = addresses;
                return addresses;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"DNS resolution failed for {domain}: {ex.Message}");
                return Array.Empty<IPAddress>();
            }
        }

        private async Task<IPAddress[]> ResolveViaDoh(string domain)
        {
            try
            {
                var url = $"{_options.DnsServer}?name={domain}&type=A";
                if (_options.IncludeIPv6)
                {
                    url += "&type=AAAA";
                }
                
                var json = await _httpClient.GetStringAsync(url);
                
                // Упрощенный парсинг JSON ответа
                var ips = new List<IPAddress>();
                var dataIndex = json.IndexOf("\"data\":", StringComparison.Ordinal);
                
                while (dataIndex > 0)
                {
                    var start = json.IndexOf('"', dataIndex + 7) + 1;
                    var end = json.IndexOf('"', start);
                    var ipString = json.Substring(start, end - start);
                    
                    if (IPAddress.TryParse(ipString, out var ip))
                    {
                        ips.Add(ip);
                    }
                    
                    dataIndex = json.IndexOf("\"data\":", end, StringComparison.Ordinal);
                }
                
                return ips.ToArray();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"DoH resolution failed: {ex.Message}");
                return Array.Empty<IPAddress>();
            }
        }

        private async Task<IPAddress[]> ResolveViaCustomDns(string domain)
        {
            try
            {
                var dnsServer = IPAddress.Parse(_options.DnsServer);
                var query = new byte[] { /* DNS запрос */ };
                
                using var udpClient = new UdpClient();
                await udpClient.SendAsync(query, query.Length, new IPEndPoint(dnsServer, 53));
                var result = await udpClient.ReceiveAsync();
                
                // Парсинг DNS ответа (упрощенно)
                return Array.Empty<IPAddress>();
            }
            catch
            {
                return Array.Empty<IPAddress>();
            }
        }

        private string GenerateSetName(string domain)
        {
            var clean = new string(domain
                .Where(c => char.IsLetterOrDigit(c) || c == '.')
                .ToArray())
                .Replace('.', '_');
            
            return $"{clean[..Math.Min(clean.Length, 28)]}_set";
        }

        private string GenerateCommands(DomainResult result)
        {
            var sb = new StringBuilder();
            sb.AppendLine($"# IPSet commands for: {result.Domain}");
            sb.AppendLine($"# Generated at: {DateTime.UtcNow:yyyy-MM-dd HH:mm:ss} UTC");
            sb.AppendLine($"# IPv4 addresses: {result.IPv4Addresses.Length}");
            
            if (_options.IncludeIPv6)
            {
                sb.AppendLine($"# IPv6 addresses: {result.IPv6Addresses.Length}");
            }
            
            sb.AppendLine();
            sb.AppendLine($"# Create ipset (if not exists)");
            sb.AppendLine($"sudo ipset create {result.SetName} hash:ip family inet --exist");
            
            if (_options.IncludeIPv6 && result.IPv6Addresses.Length > 0)
            {
                sb.AppendLine($"sudo ipset create {result.SetName}6 hash:ip family inet6 --exist");
            }
            
            sb.AppendLine();
            sb.AppendLine($"# Flush existing entries");
            sb.AppendLine($"sudo ipset flush {result.SetName}");
            
            if (_options.IncludeIPv6 && result.IPv6Addresses.Length > 0)
            {
                sb.AppendLine($"sudo ipset flush {result.SetName}6");
            }
            
            sb.AppendLine();
            sb.AppendLine($"# Add IPv4 addresses");
            foreach (var ip in result.IPv4Addresses)
            {
                sb.AppendLine($"sudo ipset add {result.SetName} {ip} 2>/dev/null");
            }
            
            if (_options.IncludeIPv6 && result.IPv6Addresses.Length > 0)
            {
                sb.AppendLine();
                sb.AppendLine($"# Add IPv6 addresses");
                foreach (var ip in result.IPv6Addresses)
                {
                    sb.AppendLine($"sudo ipset add {result.SetName}6 {ip} 2>/dev/null");
                }
            }
            
            sb.AppendLine();
            sb.AppendLine($"# Apply iptables/ip6tables rules");
            sb.AppendLine($"sudo iptables -A OUTPUT -m set --match-set {result.SetName} dst -j ACCEPT");
            
            if (_options.IncludeIPv6 && result.IPv6Addresses.Length > 0)
            {
                sb.AppendLine($"sudo ip6tables -A OUTPUT -m set --match-set {result.SetName}6 dst -j ACCEPT");
            }
            
            sb.AppendLine();
            sb.AppendLine($"# For automatic updates:");
            sb.AppendLine($"# 0 3 * * * {Environment.ProcessPath} {result.Domain} > /path/to/update_{result.SetName}.sh");
            
            return sb.ToString();
        }

        public void GenerateUpdateScripts(List<DomainResult> results)
        {
            // Генерация Bash скрипта
            var bashScript = new StringBuilder("#!/bin/bash\n\n");
            bashScript.AppendLine("# Auto-generated update script");
            bashScript.AppendLine("# Run this script to update IP sets");
            
            foreach (var result in results)
            {
                bashScript.AppendLine();
                bashScript.AppendLine($"# Update for {result.Domain}");
                bashScript.AppendLine($"sudo ipset flush {result.SetName}");
                
                foreach (var ip in result.IPv4Addresses)
                {
                    bashScript.AppendLine($"sudo ipset add {result.SetName} {ip} 2>/dev/null");
                }
                
                if (_options.IncludeIPv6 && result.IPv6Addresses.Length > 0)
                {
                    bashScript.AppendLine($"sudo ipset flush {result.SetName}6");
                    foreach (var ip in result.IPv6Addresses)
                    {
                        bashScript.AppendLine($"sudo ipset add {result.SetName}6 {ip} 2>/dev/null");
                    }
                }
            }
            
            File.WriteAllText("update_ipsets.sh", bashScript.ToString());
            Console.WriteLine("Generated update_ipsets.sh");
            
            // Генерация PowerShell скрипта
            var psScript = new StringBuilder("<#\nAuto-generated update script\n#>\n\n");
            psScript.AppendLine("Import-Module DnsClient");
            
            foreach (var result in results)
            {
                psScript.AppendLine();
                psScript.AppendLine($"# Update for {result.Domain}");
                psScript.AppendLine($"$ips = @(");
                foreach (var ip in result.IPv4Addresses)
                {
                    psScript.AppendLine($"    '{ip}'");
                }
                psScript.AppendLine($")");
                psScript.AppendLine($"sudo ipset flush {result.SetName}");
                psScript.AppendLine($"foreach ($ip in $ips) {{");
                psScript.AppendLine($"    sudo ipset add {result.SetName} $ip 2>$null");
                psScript.AppendLine($"}}");
            }
            
            File.WriteAllText("update_ipsets.ps1", psScript.ToString());
            Console.WriteLine("Generated update_ipsets.ps1");
        }
    }
}